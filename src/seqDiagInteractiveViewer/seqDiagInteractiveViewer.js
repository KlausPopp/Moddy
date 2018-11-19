/**
 * Moddy sequence diagram interactive viewer
 * Author: klauspopp@gmx.de
 * Licence: GPLV2
 */

'use strict'

/*
 * TODO
 * Support time range
 * 
 */
const g_viewerName = "moddy sd interactive viewer";
const g_version = "0.2";


var g_diagramArgs = getDiagramArgs( g_moddyDiagramArgs );
var g_lay = new DrawingLayout(g_moddyDiagramParts, g_moddyTracedEvents);
var g_tooltipControl = new TooltipControl(g_lay);
//Data arrays for d3
var g_traceData = {
	msgLines: { data: [] },	// data for message lines (<MSG, T-EXP), refs to g_moddyTracedEvents
	boxes:    { data: [] },	// data for boxes (STA, VC), refs to g_moddyTracedEvents
	annLines: { data: [] },	// data for annotation lines (ANN, ASSFAIL), refs to g_moddyTracedEvents
	labels:   { data: [] },	// data for labels (all types), SdLabel objects
	lifelines: { }
}
  
distributeTraceData();

var g_timeScaleControl = new TimeScaleControl(g_lay, g_traceData);
updateDrawing( g_lay, g_traceData, { hideNonVisible: true, reposLabels: true});
	
var g_windowChangeControl = new WindowChangeControl(g_lay, g_timeScaleControl, g_traceData);

//---------------------------------------------------------------------------------
// Diagram formatting options
//
function getDiagramArgs( overrideValues ) {
	var defaults = {
		title: '',
		timePerDiv: 1.0,
		pixPerDiv: 25,
		partSpacing: 300,
		partBoxSize: {w: 100, h:60},
		statusBoxWidth: 20,
		variableBoxWidth: 120,
		varSpacing: 180,
		font: "9pt Verdana, sans-serif"
	}	

	for(let key of Object.keys(overrideValues)) {
		defaults[key] = overrideValues[key]
	}
	return defaults;
}

//---------------------------------------------------------------------------------
// Layout Engine.
//
function DrawingLayout( partArray, moddyTracedEvents ) {
	var that = this;
	
	this.diagram = {
		div 	: undefined			// diagram div d3 object
	}

	this.canvas = {

		mh : {
			main : { },					// main canvas d3 object and ctx
			hidden : { }				// hidden canvas d3 object and ctx
		},
		
		// in pixels
		top 	: undefined,		// absolute top of canvas
		left	: undefined,		// absolute left of canvas
		width	: undefined,		// canvas width EXCLUDING left margin
		fullWidth : undefined,		// canvas width INCLUDING left margin
		height	: undefined,		// canvas height
		margin: {
			top: 20,				// Y-offset to begin of drawing area 
			right: 20,				// X right border of drawing area
			left: 80				// X-offset to begin of drawing area
		},
		yT0 : undefined,			// screen Y position of time=0 when no scrolling is applied

	}
	
	this.parts = {
		div: undefined,				// parts div d3 object
		svg: undefined,				// parts svg d3 object 
		dragLastX: undefined,		// last mouse X during dragging
		maxNameWidth: undefined,	// max text width for part name
	}
	this.scrollDummy = {
		div: undefined,				// scrolldummy div d3 object
	}
	
	this.scaling = {
		initialSceneHeight : undefined,	// initial scene height (as defined by g_diagramArgs)
		sceneHeight: undefined,		// actual scene height 	
		maxTs : undefined,			// highest timestamp in scene
		scaleFactor: 1.0,			// actual time scale factor
		timeOffset: 0, 				// first time shown in scene
		yScale: undefined, 			// time to Y scaling function
	}
	
	//-------------------------------------------------------------
	/// Functions
	
	// set x position of all partArray entries
	// @return compute width based on the parts
	this.computePartXCenter = function ()	{
		
		var width = 0;
		var idx = 0;
		
		for(let part of partArray){
			if( idx == 0)
			 	width += g_diagramArgs.partBoxSize.w/2+60;
			else {
				if(part.tp == "Part")
				 	width += g_diagramArgs.partSpacing;
				else if(part.tp == "Var")
				 	width += g_diagramArgs.varSpacing;
				else
					throw 'Invalid part type ' + part.tp;
			}
			part.centerX = width;
			
			idx++;	
		}
		width += this.spacingAfterLastPart();
		return width;
	} 

	this.spacingAfterLastPart = function(){
		return g_diagramArgs.partSpacing + this.canvas.margin.right;
	}
	
	// add <dx> to the centerX of part <idx> and all parts on the right to part  
	this.modifyPartCenter = function( idx, dx){
		
		let leftLimit = (idx == 0) ? 50 : partArray[idx-1].centerX + 50;
		
		if( partArray[idx].centerX + dx >= leftLimit){
			
			for( ; idx < partArray.length; idx++){
				let part = partArray[idx];
				part.centerX += dx;
			}
			
			this.setLogicalCanvasWidth( partArray.slice(-1)[0].centerX + this.spacingAfterLastPart() )
			return true;
		}
		return false;
	}
	
	this.partCenterX = function( partNo ){
		if (partNo == -1)
			return 0;	// "global" part 
		if (partNo >= partArray.length)
			return this.canvas.width;
		return partArray[partNo].centerX;
	}
	
	// create SVG for parts, set parts.d3 and parts.svg
	this.initParts = function(){
		this.parts.div = d3.select("body").select("#parts")
		this.parts.svg = this.parts.div
			.append("svg")
		    .attr("width", "100%")
		    .attr("height", g_diagramArgs.partBoxSize.h)
			.style("margin-left", this.canvas.margin.left + "px");
		
	}
	
	// Draw part boxes using d3 
	this.initPartBoxes = function(){
		var groups = this.parts.svg.selectAll('g').data(partArray)
			.enter().append('g')
		   	.call(d3.drag()
		        .on("start", this.partDragStarted)
		        .on("drag", this.partDragged)
		        .on("end", this.partDragEnded))
			;
		
		
		groups.append('rect')
			.attr('stroke', 'black')
			.attr('stroke_width', 1)
			.attr('fill', 'ghostwhite')
			.attr('x', function(d) { return 0; } )
			.attr('y', function(d) { return 0;} )
			.attr('height', function(d) { return g_diagramArgs.partBoxSize.h;} );
		
		this.parts.maxNameWidth = g_diagramArgs.partBoxSize.w;

		groups.append('text')
		.text( function(d) { return d.name; })
		.attr('text-anchor', function(d) { return 'middle'; })
		.each( this.determineMaxPartNameWidth )
		;
		
		this.updatePartBoxes();
	}
	
	this.determineMaxPartNameWidth = function(d,i){
		//console.log( "determineMaxPartNameWidth", d.name, d3.select(this).node().getComputedTextLength());
		let width = d3.select(this).node().getComputedTextLength() + 8;
		that.parts.maxNameWidth = Math.min(Math.max( that.parts.maxNameWidth, width), g_diagramArgs.partSpacing + 6 );
	}
	
	// Update part boxes with possibly modified data (in partArray) 
	this.updatePartBoxes = function(){
		var groups = this.parts.svg.selectAll('g')
		.attr("transform", function(d) { return "translate(" + (d.centerX - that.parts.maxNameWidth/2) +",0)" })
		;
		
		groups.selectAll('rect')
			.attr('width', this.parts.maxNameWidth );
		
		groups.selectAll('text')
			.text( function(d) { return d.name; })
			.attr('x', function(d) { return that.parts.maxNameWidth/2; } )
			.attr('y', function(d) { return g_diagramArgs.partBoxSize.h/2; } )

	}

	// Part dragging
	this.partDragStarted = function(d,i) {
		console.debug("partDragStarted ", d, i, d3.event.x)
		that.parts.dragLastX = d3.event.x;
		d3.select(this).raise().classed("active", true);
	}
	this.partDragged = function(d,i) {
		let dx = d3.event.x - that.parts.dragLastX;	// compute how much dragged in X direction
		that.parts.dragLastX = d3.event.x;
		that.modifyPartCenter( i, dx );					// update part and all parts on the right
		that.updatePartBoxes();
		g_windowChangeControl.resized();

	}

	this.partDragEnded = function(d){
		d3.select(this).classed("active", false);
	}
	
	// Parts and Diagram are "fixed" divs. Do scrolling manually...
	this.setHorizontalScroll = function(scrollX){
		this.parts.div.style("left", -scrollX + this.canvas.left + "px");
		this.diagram.div.style("left", -scrollX + this.canvas.left + "px");
	}
	
	//--------------------------------------------------
	// CANVAS
	
	// Determine canvas absolute top position
	this.getCanvasTop = function(){
		return this.parts.div.node().offsetTop + this.parts.div.node().offsetHeight;
	}
		
	// create main and hidden canvas for diagram, set diagram.div
	this.initDiagram = function(){
		this.diagram.div = d3.select("body").select("#diagram");
		
		this.canvas.mh.main = this.createCanvas();
		this.canvas.mh.hidden = this.createCanvas();
		this.canvas.mh.hidden.d3.classed('hiddenCanvas', true);
		
		let bbox = this.diagram.div.node().getBoundingClientRect();
		this.canvas.top = this.getCanvasTop();
		this.canvas.left = bbox.left;
		this.diagram.div.style("top", this.canvas.top+"px")
	}

	this.createCanvas = function(){
		var rv = {};
		rv.d3 = this.diagram.div.append("canvas")
	   
	    rv.ctx = rv.d3.node().getContext('2d');
		return rv;
	}
	
	this.canvasResize = function (){
		var width = this.canvas.fullWidth;
		var height = this.canvas.height = visualViewPortHeight() - this.canvas.top;
		
		for( let cavs of Object.keys(this.canvas.mh)){
			this.canvas.mh[cavs].d3.attr('height', height);
			this.canvas.mh[cavs].d3.attr('width', width);
		}
		// rescale only the main canvas (keep hidden canvas ratio 1:1)
		rescaleCanvas(this.canvas.mh.main.d3.node());
		this.canvas.mh.main.ctx.font = g_diagramArgs.font;
	}

	// call canvasFunction for the main and hidden context
	this.canvasCallCtx = function( canvasFunction, ...rest ) {
		
		for( let cavs of Object.keys(this.canvas.mh))
			this.canvas.mh[cavs].ctx[canvasFunction].apply( this.canvas.mh[cavs].ctx, rest);
	}

	// clear the main and hidden canvas 
	this.canvasClear = function(){
		for( let cavs of Object.keys(this.canvas.mh))
			g_lay.canvas.mh[cavs].ctx.clearRect( 0, 0, this.canvas.fullWidth, this.canvas.height); 
	}

	this.obtainTextHeight = function(){
		
		// there is no function to measure the text height
		// get a very close approximation of the vertical height by checking the length of a capital M.
		return this.canvas.mh.main.ctx.measureText('M').width;
	}
	
	this.obtainTextWidth = function( text ){
		return this.canvas.mh.main.ctx.measureText(text).width;
	}

	this.screen2CanvasY = function( screenY ){
		return screenY - this.canvas.top;
	}
	
	this.canvas2ScreenY = function( canvasY ){
		return canvasY + this.canvas.top;
	}
	
	this.setLogicalCanvasWidth = function( width ){
		this.canvas.width = width;
		this.canvas.fullWidth = width + this.canvas.margin.left;		
	}
	//--------------------------------------------------
	// SCROLLDUMMY

	this.initScrollDummy = function(){
		this.scrollDummy.div = d3.select("body").select("#scrollDummy").style("width", this.canvas.fullWidth + "px");;
	}
	
	this.scrollDummyUpdate = function(){
		// adjust the height of the scrollDummy div to the new height so 
		// the browser shows the scrollbar accordingly
		var height = this.scaling.sceneHeight + this.canvas.top + this.canvas.margin.top;
		this.scrollDummy.div.style("height", height + "px");
		this.scrollDummy.div.style("width", this.canvas.fullWidth + "px");
	}
		
	
	//--------------------------------------------------
	// SCALING
	

	// get timestamp of last event in trace
	this.getMaxTs = function(){
		var lastTs = 0;
		
		if( moddyTracedEvents.length > 0 ){
			lastTs = moddyTracedEvents[moddyTracedEvents.length -1].t;
		}
		return lastTs;
	}
	this.getInitialSceneHeight = function(){
		var timePerPx = g_diagramArgs.timePerDiv / g_diagramArgs.pixPerDiv;
		return this.scaling.maxTs / timePerPx;
	}

	this.sceneChangeTimeScale = function( newTimeScale ){
		this.sceneChangeHeight( this.scaling.initialSceneHeight * newTimeScale);
	}
	
	this.sceneChangeHeight = function( newHeight ){
		this.scaling.sceneHeight = newHeight;
		
		// change scale
		this.scaling.scaleFactor = newHeight / this.scaling.initialSceneHeight;
		this.scaling.yScale.range([0, newHeight]).domain([0, this.scaling.maxTs]);
		
	}

	// convert simulation time to canvas Y position
	this.time2CanvasY = function(t){
		return this.scaling.yScale(t - this.scaling.timeOffset) + this.canvas.margin.top;
	}

	// Get the simulation time at screenY position
	// @param screenY - viewport Y position  
	// @return (simulation) time
	this.screenY2Time = function( screenY ){
		return this.y2Time( screenY - this.canvas.yT0 ) + this.scaling.timeOffset;	
	}

	
	
	// Get the simulation time at canvasY position
	// @param canvasY - canvas Y position  
	// @return (simulation) time
	this.canvasY2Time = function( canvasY ){
		return this.y2Time( canvasY - this.canvas.margin.top ) + this.scaling.timeOffset;	
	}
	
	this.y2Time = function(y){
		return y / this.scaling.sceneHeight * this.scaling.maxTs;
	}
	
	this.getVisibleTimeRange = function () {
		var rangeEnd = Math.min(g_lay.canvasY2Time(g_lay.canvas.height), g_lay.scaling.maxTs);
		var rangeStart = g_lay.canvasY2Time(0);
		//console.log("range Start %f End %f", rangeStart, rangeEnd)
		return {start: rangeStart, end: rangeEnd }
	}
	
	this.setTimeOffset = function(offset){
		this.scaling.timeOffset = offset;
	}
	
	/// TITLE and version
	this.initTitle = function(){
		let titleDiv = d3.select("body").select("#title");
		
		titleDiv.append("div")
			.style("float", "left")
			.style("padding-left", "20px")
			.append("p")
			.html(g_diagramArgs.title == "" ? "(Untitled)" : g_diagramArgs.title);

		titleDiv.append("div")
			.style("float", "right")
			.style("padding-right", "20px")
			.append("p")
			.html(g_viewerName + " " + g_version);
	}
	
	
	/// INIT
	this.initTitle();
	this.setLogicalCanvasWidth(this.computePartXCenter());
	this.initParts();
	this.initPartBoxes();
	
	this.initDiagram();
	this.canvas.yT0 = this.canvas.top + this.canvas.margin.top;
	
	this.scaling.maxTs = this.getMaxTs();
	this.scaling.initialSceneHeight = this.getInitialSceneHeight();

	this.initScrollDummy();

	this.scaling.yScale = d3.scaleLinear();
	this.sceneChangeHeight( this.scaling.initialSceneHeight );
	
	this.canvasResize();
}

//---------------------------------------------------------------------------------
/// YAxis

function yAxisTickSteps(){
	var divPx = 60; 	
	
	var timeUnitsPerDiv = g_lay.scaling.maxTs*1E15/g_lay.scaling.sceneHeight*divPx;	// How much time in one div
	var logTuPerDiv = Math.log10(timeUnitsPerDiv);
	var floorlogTuPerDiv = Math.floor(logTuPerDiv);
	var rv;
	
	if( logTuPerDiv > (floorlogTuPerDiv + Math.log10(5)))
		rv = Math.pow(10,floorlogTuPerDiv) * 5;
	else if( logTuPerDiv > (floorlogTuPerDiv + Math.log10(2)))
		rv = Math.pow(10,floorlogTuPerDiv) * 2;
	else
		rv = Math.pow(10,floorlogTuPerDiv);
	rv /= 1E15;
	//console.log ("yAxisTickSteps %f timeUnitsPerDiv %.3f logTuPerDiv %.3f ",  rv, timeUnitsPerDiv, logTuPerDiv);
	return rv;
	
}
function yAxisformatTickValue(time, steps)
{
	var rv;
	var fmt = ".0f"
	if( steps >= 1.0) rv = d3.format(fmt)(time) + " s";	
	else if( steps >= 1E-3) rv = d3.format(fmt)(time*1E3) + " ms";	
	else if( steps >= 1E-6) rv = d3.format(fmt)(time*1E6) + " us";	
	else if( steps >= 1E-9) rv = d3.format(fmt)(time*1E9) + " ns";
	else if( steps >= 1E-12) rv = d3.format(fmt)(time*1E12) + " ps";
	return rv;
}

function drawYAxisTick(ctx, y, width){
	ctx.beginPath();
	ctx.lineWidth = 0.3;
	ctx.strokeStyle = "grey";
	ctx.moveTo( 0, y);
	ctx.lineTo( width, y);
	ctx.stroke();
}

function drawYAxisText(ctx, time, steps, y){
	ctx.textAlign = "end";
	ctx.fillStyle = "grey";
	ctx.fillText( yAxisformatTickValue(time, steps), -5, y+5);
}

function yAxisRedraw()
{
	var timerange = g_lay.getVisibleTimeRange();
	var steps = yAxisTickSteps();
	var t = Math.max(timerange.start - (timerange.start%steps), 0);
	
	for( ; t<=timerange.end; t+=steps){
		drawYAxisTick(g_lay.canvas.mh.main.ctx, g_lay.time2CanvasY(t), g_lay.canvas.width);
		drawYAxisText(g_lay.canvas.mh.main.ctx, t, steps, g_lay.time2CanvasY(t));
	}
}


  
//---------------------------------------------------------------------------------
// Parse moddy trace data



// Distribute g_moddyTracedEvents into the different g_traceData objects so that
// there is a 1:1 relation between the data and the traced objects
function distributeTraceData(){
	g_traceData.msgLines.data = [];
	g_traceData.boxes.data = [];
	g_traceData.annLines.data = [];
	g_traceData.labels.data = [];
	
	for( let e of g_moddyTracedEvents){
		
		
		var refLine = { xo1:0, xo2:0}, anchor="center", color="black", allowBelowLine=false;
		var targetPoint = null;
		
		// create the label object
		switch(e.tp){
		case "<MSG":
			refLine.p1 = e.p;
			refLine.y1 = e.b;
			refLine.p2 = e.s;
			refLine.y2 = e.t;
			allowBelowLine = true;
			break;
		case "T-EXP":
			refLine.p1 = refLine.p2 = e.p;
			refLine.xo1 = -150;
			refLine.y1 = refLine.y2 = e.t;
			allowBelowLine = true;
			color = "blue";
			anchor="end";
			break;
		case "STA":
			refLine.p1 = refLine.p2 = e.p; 
			refLine.xo1 = refLine.xo2 = -10;
			refLine.y1 = e.b; 
			refLine.y2 = e.t;
			anchor="start";
			break;
		case "VC":
			refLine.p1 = refLine.p2 = e.p; 
			refLine.xo1 = -g_diagramArgs.variableBoxWidth/2;
			refLine.xo2 = +g_diagramArgs.variableBoxWidth/2;
			refLine.y1 = refLine.y2 = e.b + (e.t-e.b)/2;
			break;
		case "ANN":
		case "ASSFAIL":
			refLine.p1 = e.p;
			refLine.xo1 = +22;
			refLine.p2 = e.p+1; 
			refLine.y1 = refLine.y2 = e.t;
			color = "red";
			anchor="start";
			targetPoint = {p: e.p, xo: 0, y: e.t}
			allowBelowLine = true;
			break;
		}
		if( 'c' in e)
			color = e.c;
		
		var sdl = new SdLabel( refLine, anchor, e.txt, color, g_lay, targetPoint, allowBelowLine );
		g_traceData.labels.data.push( sdl );

		switch(e.tp){
		case "<MSG":
		case "T-EXP":
			g_traceData.msgLines.data.push(e);
			break;
		case "STA":
		case "VC":
			g_traceData.boxes.data.push(e);
			break;
		case "ANN":
		case "ASSFAIL":
			g_traceData.annLines.data.push(sdl);
			break;
		}

	}
}

    

/**
 * Constructor for sequence diagram label. For labels that shall be auto-positioned
 * to avoid collisions
 * @param {Array} 	refLine 	line on which the text can be moved to get out of the way
 *							   	with indexes [p1,xo1,y1,p2,xo2,y2] y=unscaled. 
 *								p1/p2 are the part numbers in the scene 
 *								xo1/xo2 are the x offsets from the part center
 * @param {String} 	anchor	 	text alignment ("start", "center", "end")
 * @param {String} 	text		label text
 * @param {String} 	color		text color
 * @param {Object}	lay			layout object 
 * @param {Point}	targetPoint	Point where the label belongs to (may be null) {p, xo, y}
 * @param {Bool}	allowBelowLine if true, positioning below refLine is allowed
 */ 
function SdLabel( refLine, anchor, text, color, lay, targetPoint, allowBelowLine ) {
	const vDistAboveLine = -3;
	this.vDist = vDistAboveLine;			// pixels above the line
	this.curText = text;
	this.curTextWidth = null;
	this.curTextHeight = null;
	this.fullText = text;
	this.color = color;
	this.targetPoint = targetPoint;
	this.refLine = refLine;
	
	this.currentTextPolygonCache = undefined;
	this.currentRefLinePolygonCache = undefined;
	
	
	this.getText = function() { return this.curText; }

	this.setText = function(newText){
		this.curText = newText;
		this.curTextWidth = null;
	}

	this.getTextWidth = function() {
		if(this.curTextWidth == null ) 
			this.curTextWidth = lay.obtainTextWidth(this.curText);
		return this.curTextWidth;
	}
	this.getTextHeight = function(){
		if( this.curTextHeight == null)
			this.curTextHeight = lay.obtainTextHeight();

		return this.curTextHeight;
	}
	
	this.idealHPos = function() {
		var hPos; 
		switch(anchor){
		case "start": hPos = 0; break;
		case "center": hPos = 0.5; break;
		case "end": hPos = 1; break;
		default: throw "bad anchor" + anchor;
		}
		return hPos;
	}
	this.hpos = this.idealHPos();	// relative position on the refLine 0..1 (0=begin 1=end)
	
	this.getAnchor = function() { return anchor }
		
	// compute polygon covering the label text
	// @param hpos: relative position on reference line (0=begin, 1=end)
	// @param height: text height
	// @param width: text width
	// @return {Array} with polygon points (scaled)
	this.getTextPolygon = function( hpos, vDist, height, width ) {
		var rv =  [];
		
		var center = this.getCenter(hpos, vDist);
		var theta = this.getCurrentRotation()
		
		switch(anchor){
		case "start":		
			rv.push( rotatePoint( { x: center.x, y: center.y }, 					center, theta));
			rv.push( rotatePoint( { x: center.x, y: center.y-height }, 				center, theta));
			rv.push( rotatePoint( { x: center.x + width, y: center.y-height }, 		center, theta));
			rv.push( rotatePoint( { x: center.x + width, y: center.y }, 			center, theta));
			break;
		case "center":		
			rv.push( rotatePoint( { x: center.x - width/2, y: center.y }, 			center, theta));
			rv.push( rotatePoint( { x: center.x - width/2, y: center.y-height }, 	center, theta));
			rv.push( rotatePoint( { x: center.x + width/2, y: center.y-height }, 	center, theta));
			rv.push( rotatePoint( { x: center.x + width/2, y: center.y }, 			center, theta));
			break;
		case "end":		
			rv.push( rotatePoint( { x: center.x - width, y: center.y }, 			center, theta));
			rv.push( rotatePoint( { x: center.x - width, y: center.y-height }, 		center, theta));
			rv.push( rotatePoint( { x: center.x, y: center.y-height }, 				center, theta));
			rv.push( rotatePoint( { x: center.x, y: center.y }, 					center, theta));
			break;
		}
			
		return rv;
	}
	
	this.resetPolygonCache = function() {
		this.currentTextPolygonCache = undefined;
		this.currentRefLinePolygonCache = undefined;
	}
	
	this.getCurrentTextPolygon = function(){
		if( this.currentTextPolygonCache == undefined ){		
			this.currentTextPolygonCache = this.getTextPolygon( this.hpos, this.vDist, this.getTextHeight(), this.getTextWidth())
		}
		return this.currentTextPolygonCache
	}
	
	
	// get the polygon that the whole refLine covers including space for text below (if allowBelowLine is set)
	// and above line
	this.getCurrentRefLinePolygon = function(){
		if( this.currentRefLinePolygonCache == undefined ){		
			var rv =  [];
			let center = this.getCenter(0.5, (allowBelowLine ? this.getTextHeight() : 0));
			let theta = this.getCurrentRotation();
			let height = (this.getTextHeight()* (allowBelowLine ? 2 : 1)) - vDistAboveLine;
			let width = this.getRefLineLength();
	
			rv.push( rotatePoint( { x: center.x - width/2, y: center.y }, 			center, theta));
			rv.push( rotatePoint( { x: center.x - width/2, y: center.y-height }, 	center, theta));
			rv.push( rotatePoint( { x: center.x + width/2, y: center.y-height }, 	center, theta));
			rv.push( rotatePoint( { x: center.x + width/2, y: center.y }, 			center, theta));
			this.currentRefLinePolygonCache = rv;
		}
		return this.currentRefLinePolygonCache;
	}
	
	// compute the x-position of <partNo> considering xOffset to the partNo center
	this.xPos = function( partNo, xOffset ){
		return lay.partCenterX( partNo ) + xOffset;
	}
	
	// return length of refLine scaled
	this.getRefLineLength = function(){
		// compute lenght of refline scaled
		var a = (this.xPos(refLine.p2, refLine.xo2)  - this.xPos(refLine.p1, refLine.xo1));
		var b = lay.scaling.yScale(refLine.y2 - refLine.y1);
		return Math.sqrt(a*a + b*b);		
	}

	
	// compute how much percent of reference line the text covers (0..1)
	this.getTextWidthPercent = function(){
		var p = this.getTextWidth() / this.getRefLineLength();
		//console.log("getTextWidthPercent %s %f%", text, p * 100);
		return p;
	}
	
	// return {x:,y:} coordinates of text anchor (considering current pos on refLine)
	this.getCurrentCenter = function() {
		return this.getCenter(this.hpos, this.vDist);
	}

	// compute text center
	// @param hpos: relative position on reference line (0=begin, 1=end)
	// @param vDistPx: vertical distance from line in css px (positive=below line, negative=above line)
	// @return {x:,y:} coordinates of center point (perpendicular point to refLine)  
	this.getCenter = function( hPos, vDistPx){
		var refLinePoint = this.getCenterOnRefLine(hPos);
		var a = this.getCurrentRotation();
		return rotatePoint( {x: refLinePoint.x+vDistPx, y:refLinePoint.y}, refLinePoint, Math.PI/2 + a );
	}

	// return {x:,y:} coordinates of text anchor (considering pos parameter)
	this.getCenterOnRefLine = function(hpos) {
		var rv = {};
		let x1 = this.xPos( refLine.p1, refLine.xo1 ); 
		let x2 = this.xPos( refLine.p2, refLine.xo2 ); 

		rv.x = ( x1 + (x2 - x1) * hpos);
		rv.y = lay.time2CanvasY( refLine.y1 + (refLine.y2 - refLine.y1) * hpos);
		return rv;
	}

	// return: rotation of scaled refLine in radians
	this.getCurrentRotation = function() {
		return Math.atan( 
				(lay.scaling.yScale(refLine.y2 - refLine.y1)) / 
				((this.xPos( refLine.p2, refLine.xo2 ) - this.xPos( refLine.p1, refLine.xo1 ))))
	}
	
	this._trimTry = function( nChars, ellipsis ) {
		var newText = text.substr(0,nChars);
		if( ellipsis ) newText += "\u2026";
		this.setText(newText);
		return this.getTextWidth();		
	}
	
	// trim text to <maxPx> pixels. Store trimmed text in self.curText 
	this.trimTextToPx = function( maxPx ){
		var nChars;
		var px;

		if( maxPx >= 0 && this._trimTry( text.length, false ) > maxPx ){
			// try linear shrink (not exact due to non-monospaced font)
			nChars = (text.length * (maxPx / this.getTextWidth())).toFixed(0);
			px = this._trimTry( nChars, true );
			
			//console.log( "trim linshrink nc "+ nChars + " px " + px);			
			if( px > maxPx ){
				while( px > maxPx && nChars > 1){
					nChars--;
					px = this._trimTry( nChars, true );
				}
			}
			else if( px < maxPx){
				while( px < maxPx ){
					nChars++;
					px = this._trimTry( nChars, true );
				}				
			}
			if( nChars == 0 )
				this.setText("");
			//console.log( "trim finetune nc "+ nChars + " px " + px);			
		}
		return this.getText();
	}
	
	this.checkOverlap = function( labelArray, hpos, vDist, height, width ){
		var thisPolygon = this.getTextPolygon(hpos, vDist, height, width);
		var idx = 0;
		var nCollisions = 0;
		
		for(let otherLabel of labelArray) {
			
			if( otherLabel != this){
				if(doPolygonsIntersect( thisPolygon, otherLabel.getCurrentTextPolygon())){
					nCollisions += 1;
				}
			}
			idx++;
		}
		return nCollisions;
	}
	
	this.checkRefLinesMayCollide = function( otherSdLabel ){
		if( otherSdLabel == this ) return false;
		
		return doPolygonsIntersect( this.getCurrentRefLinePolygon(), otherSdLabel.getCurrentRefLinePolygon());

	}
	
	this.clipHPos = function( desiredHPos, actualWidth ){ 
		var widthPercent = actualWidth / this.getRefLineLength();

		switch(anchor){
		case "start": 
			if( desiredHPos < 0) desiredHPos = 0;
			else if( widthPercent + desiredHPos > 1) desiredHPos = 1 - widthPercent;
			break;
		case "center":
			if( desiredHPos < widthPercent/2) desiredHPos = widthPercent/2;
			else if( widthPercent/2 + desiredHPos > 1) desiredHPos = 1 - widthPercent/2;
			break;
		case "end": 
			if( desiredHPos < widthPercent) desiredHPos = widthPercent;
			else if( desiredHPos > 1) desiredHPos = 1;
			break;
		default: throw "bad anchor" + anchor;
		}
		
		return desiredHPos;
	}
	
	// Virtually move text label and check how many collisions with other labels occur
	// @param algoType - Type of movement see below
	// @param algoIter - Algorithm iteration number 0..n
	// @return { result: result, nCollisions: nCollisions, hPos: hPos, vDist: vDist, width: width }
	// 	result: "ok" - move ok, "nok" - cannot move (out of limits), "break" - reach end of possible iterations
	//  nCollisions: number of collisions occured
	//	hPos, vDist, width: Applied parameters
	//
	// AlgoTypes:
	//	{ where: "aboveLine"/"belowLine", textWidth: "normal"/"half"}
	this.tryMove = function( labelArray, algoType, algoIter ){
		var hMoveAlgo = {
			'start':  [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
			'center': [0.4, 0.6, 0.2, 0.8, 0.0, 1.0],
			'end':    [1.0, 0.8, 0.6, 0.4, 0.2, 0.0],
		}
		var nCollisions=0, hPos=0, vDist=0, width=0, result="nok";
		
		if( algoType.where == "aboveLine" || algoType.where == "default")
			vDist = -3;
		else if (algoType.where == "belowLine")
			vDist = this.getTextHeight() + 1;
		else
			throw "bad algoType" + algoType.where; 
		
		const margin = 3;
		this.setText(this.fullText);
		var tWidth = Math.min( this.getTextWidth(), Math.max(this.getRefLineLength() - margin, 0));
		if( algoType.textWidth == "half" )
			width = tWidth / 2;
		else if( algoType.textWidth == "normal" )
			width = tWidth;
		else
			throw "bad algoType" + algoType.textWidth; 
		
		
		if( algoType.where == "default" ){
			hPos = this.idealHPos();
			if( algoIter > 0)
				result = "break";
			else
				result = "ok";
		}
		else {
			var hMoveArr = hMoveAlgo[anchor];
			if( algoIter >= hMoveArr.length)
				result = "break";
			else {
				hPos = hMoveArr[algoIter];
				hPos = this.clipHPos( hPos, width);
				result = "ok";
			}
		}		
		if ( result == "ok" ){
			nCollisions = this.checkOverlap( labelArray, hPos, vDist, this.getTextHeight(), width);
		} 
		
		return { result: result, nCollisions: nCollisions, hPos: hPos, vDist: vDist, width: width };
	}
	
	// find the best position for the label (minimize collisions)
	this.findBestPosition = function( labelArray ){
		var algos = [
			{ where: "default", textWidth: "normal" },
			{ where: "aboveLine", textWidth: "normal" },
			{ where: "belowLine", textWidth: "normal" },
			{ where: "default", textWidth: "half" },
			{ where: "aboveLine", textWidth: "half" },
			{ where: "belowLine", textWidth: "half" }];
		
		var bestAlgo = { result: null, algoType: null, algoIter: -1};
		
		for(let algo of algos) {
			var algoIter = 0;
			
			if( !(algo.where == "belowLine" && allowBelowLine == false)){
				while(true){
					var moveResult = this.tryMove( labelArray, algo, algoIter );
					//console.log("moveResult ", algo.where, " ", algo.textWidth, " ", moveResult.width)
					if( moveResult.result == 'break')
						break;
					
					else if( moveResult.result == 'ok'){
						/*console.log( "fbP " + algo.where + " " + algo.textWidth 
								+ " #" + algoIter + " coll=" + moveResult.nCollisions);*/
						
						
						if( (bestAlgo.result) === null || 
								(moveResult.nCollisions < bestAlgo.result.nCollisions)){
							
							bestAlgo.result = moveResult;
							bestAlgo.algoType = algo;
							bestAlgo.algoIter = algoIter;
							
							if( moveResult.nCollisions == 0)
								break;	// we can stop if no collisions
						}
					}
					algoIter += 1;
				}
				if( moveResult.result == 'ok' && moveResult.nCollisions == 0)
					break;	// we can stop if no collisions
			}			
		}
		
		// apply best algo
		this.hpos = bestAlgo.result.hPos;
		this.vDist = bestAlgo.result.vDist;
		this.trimTextToPx( bestAlgo.result.width);
		this.resetPolygonCache();
		
		return bestAlgo;		
	}
	
	this.setDefaultPosAndText = function(){
		this.hpos = this.idealHPos();
		this.vDist = vDistAboveLine;
		this.setText(this.fullText);
		this.resetPolygonCache();
	}
		
}


function isShapeVisible( visibleRange, beginY, endY ){
	return (
		   // end or begin are in visible range
		   (endY   >= visibleRange.start && endY   <= visibleRange.end) ||
		   (beginY >= visibleRange.start && beginY <= visibleRange.end) ||
		   // begin before visible range and end after visible range
		   (endY   > visibleRange.end &&  beginY  < visibleRange.start));
}

//---------------------------------------------------------------------------------
//draw the part life lines

function drawLifeLine( ctx, from, to ){
	ctx.save();
	ctx.beginPath();
	ctx.setLineDash([5,5]);
	ctx.strokeStyle = "grey";
	ctx.lineWidth = 0.5;
	ctx.moveTo( from.x, from.y);
	ctx.lineTo( to.x, to.y);
	ctx.stroke();
	ctx.restore();
}


function updatePartLifeLines(){
	var visibleRange = g_lay.getVisibleTimeRange();
	var y0=g_lay.time2CanvasY(visibleRange.start);
	var y1=g_lay.time2CanvasY(visibleRange.end);
	
	for( let d of g_moddyDiagramParts){
		var from = { x: d.centerX, y: y0};
		var to 	 = { x: d.centerX, y: y1};
		
		drawLifeLine( g_lay.canvas.mh.main.ctx, from, to );
	}
}



//---------------------------------------------------------------------------------
/// Message line drawing

function msgLineArrowHead( from, to, angle, length){
	var dx = to.x - from.x;
	var dy = to.y - from.y;
	var theta = Math.atan2(dy, dx);
	var rad = radians(angle);
	return { x: to.x - length * Math.cos(theta + rad), 
		     y: to.y - length * Math.sin(theta + rad)};
}

function drawMsgLine( ctx, from, to, color, lost ){
	
	if( lost ){
		// shorten line if a lost message shall be drawn
		let dx = to.x - from.x;
		let dy = to.y - from.y;
		to.x = to.x - dx * 0.2;
		to.y = to.y - dy * 0.2;
	}
	ctx.beginPath();
	ctx.strokeStyle = color;
	ctx.lineWidth = 1;
	ctx.moveTo( from.x, from.y);
	ctx.lineTo( to.x, to.y);
	
	if( !lost ){
		// draw arrowhead
		const angle = 18;
		const arrowLen = 10;
		var point = msgLineArrowHead( from, to, angle, arrowLen);
		ctx.lineTo( point.x, point.y );
		ctx.moveTo( to.x, to.y);
		point = msgLineArrowHead( from, to, -angle, arrowLen);
		ctx.lineTo( point.x, point.y );
	}
	else {
		// draw "x" at end of line
		const angle = 45;
		const arrowLen = 6;
		var point = msgLineArrowHead( from, to, angle, arrowLen);
		ctx.lineTo( point.x, point.y );
		point = msgLineArrowHead( from, to, angle+180, arrowLen);
		ctx.lineTo( point.x, point.y );
		ctx.moveTo( to.x, to.y);
		point = msgLineArrowHead( from, to, -angle, arrowLen);
		ctx.lineTo( point.x, point.y );
		point = msgLineArrowHead( from, to, -angle+180, arrowLen);
		ctx.lineTo( point.x, point.y );
		
	}
	ctx.stroke();
}

function updateMsgLines(msgLinesData, updateOptions){
	var visibleRange = g_lay.getVisibleTimeRange();
	
	for( let d of msgLinesData.data ){
		if (isShapeVisible( visibleRange, (d.tp=="T-EXP") ? d.t : d.b, d.t )){
		
			var from = {}, to = {};
			from.x = (d.tp=="T-EXP") ? g_lay.partCenterX(d.p)-50 : g_lay.partCenterX(d.p);
			from.y = g_lay.time2CanvasY((d.tp=="T-EXP") ? d.t : d.b);
			to.x = (d.tp=="T-EXP") ? g_lay.partCenterX(d.p) : g_lay.partCenterX(d.s);
			to.y = g_lay.time2CanvasY(d.t);
			drawMsgLine( g_lay.canvas.mh.main.ctx, from, to, 
					('c' in d) ? d.c : (d.tp=="T-EXP") ? 'blue':'black',
					d.l == "t" ? true : false);
		}
	} 
}


//---------------------------------------------------------------------------------
/// Boxes drawing

function drawBox( ctx, x, y, width, height, strokeStyle, fillStyle ){
	ctx.fillStyle = fillStyle;
	ctx.fillRect( x, y, width, height);
	if( strokeStyle != undefined){
		ctx.lineWidth = 1;
		ctx.strokeStyle = strokeStyle;
		ctx.strokeRect( x, y, width, height);
	}
}

function updateBoxes(boxesData, updateOptions){
	var visibleRange = g_lay.getVisibleTimeRange();
	
	for( let d of boxesData.data ){
		if (isShapeVisible( visibleRange, d.b, d.t )){
			let strokeStyle = ('sc' in d) ? d.sc : 'orange';
			let fillStyle = ('fc' in d) ? d.fc : 'white';
			let width = (d.tp=="STA") ? g_diagramArgs.statusBoxWidth : g_diagramArgs.variableBoxWidth;
			let x = g_lay.partCenterX(d.p) - width/2;
			let y = g_lay.time2CanvasY(d.b);
			let height = g_lay.scaling.yScale(d.t - d.b);
			drawBox( g_lay.canvas.mh.main.ctx, x, y, width, height, strokeStyle, fillStyle);

			// draw box into hidden canvas, so that tooltip can identify status
			let rgb = g_tooltipControl.registerObj( d.txt );
			
			if( rgb != undefined)
				drawBox( g_lay.canvas.mh.hidden.ctx, x, y, width, height, undefined, rgb);

		}
	}
}

//---------------------------------------------------------------------------------
/// Annotation lines drawing

function drawAnnLine( ctx, from, to, color ){
	ctx.save();
	ctx.beginPath();
	ctx.strokeStyle = color;
	ctx.lineWidth = 0.5;
	ctx.moveTo( from.x, from.y);
	ctx.lineTo( to.x, to.y);
	ctx.stroke();
	ctx.restore();
}

function updateAnnLines(annLinesData, updateOptions){
	
	var visibleRange = g_lay.getVisibleTimeRange();
	
	for( let d of annLinesData.data ){
		if (isShapeVisible( visibleRange, d.refLine.y1, d.refLine.y2 )){
			var from = { x: d.xPos(d.targetPoint.p, d.targetPoint.xo), y: g_lay.time2CanvasY(d.targetPoint.y) };
			var to   = { x: d.getCurrentCenter().x - 1, y: d.getCurrentCenter().y - 4 };
			
			drawAnnLine( g_lay.canvas.mh.main.ctx, from, to, d.color );
		}
	}	
}

//---------------------------------------------------------------------------------
/// Label drawing

function drawLabel(ctx, text, anchorPoint, textAlign, rotation, fillStyle){
	
	ctx.save();
	ctx.translate(anchorPoint.x, anchorPoint.y);
	ctx.rotate( rotation );
	ctx.textAlign = textAlign;
	ctx.fillStyle = fillStyle;
	ctx.fillText( text, 0, 0);
	ctx.restore();
}

function drawLabelPolygon( ctx, polygon, fillStyle ){
	ctx.fillStyle = fillStyle;
	//console.log("fillStyle ", fillStyle)
	ctx.beginPath();
	ctx.moveTo( polygon[0].x, polygon[0].y);
	ctx.lineTo( polygon[1].x, polygon[1].y);
	ctx.lineTo( polygon[2].x, polygon[2].y);
	ctx.lineTo( polygon[3].x, polygon[3].y);
	ctx.closePath();
	ctx.fill();	
}


function updateLabels(labelsData, updateOptions){

	//console.time('updateLabels');
	// filter visible labels
	var visibleRange = g_lay.getVisibleTimeRange();	
	var visibleLabels = [];
	for( let sdl of labelsData.data ){
		if (isShapeVisible( visibleRange, sdl.refLine.y1, sdl.refLine.y2 )){
			sdl.resetPolygonCache();
			visibleLabels.push(sdl);
		}
	}
	
	for( let d of visibleLabels){
		let possiblyCollidingLabels = [];
		
		if( visibleLabels.length < 100){

			// determine which labels may possibly collide (using the polygons around the labels refLine)
			for( let otherLabel of visibleLabels )
				if( d.checkRefLinesMayCollide( otherLabel ))
					possiblyCollidingLabels.push(otherLabel);
			
			// virtually move around label to avoid overlapping text
			d.findBestPosition(possiblyCollidingLabels);
		}
		else {
			// too many objects... Avoid placing labels
			d.setDefaultPosAndText();
		}
		
		// just for debugging 
		//drawLabelPolygon( g_lay.canvas.mh.main.ctx, d.getCurrentTextPolygon(), "pink"); 
		//drawLabelPolygon( g_lay.canvas.mh.main.ctx, d.getCurrentRefLinePolygon(), "pink"); 
		drawLabel( g_lay.canvas.mh.main.ctx, 
				d.getText(),
				d.getCurrentCenter(),
				d.getAnchor(),
				d.getCurrentRotation(),
				d.color);
		
		// draw label polygon into hidden canvas, so that tooltip can identify label
		let rgb = g_tooltipControl.registerObj( d.fullText );
		
		if( rgb != undefined)
			drawLabelPolygon( g_lay.canvas.mh.hidden.ctx, d.getCurrentTextPolygon(), rgb);
	}
	//console.timeEnd('updateLabels');
	
}
	 
//
// Update the whole szene after
// Y-scale change, scrolling, resizing
// @param lay DrawingLayout
// @param traceData usually g_traceData
// @param updateOptions { reposLabels: true/false  }
//
function updateDrawing(
		lay,
		traceData, 
		updateOptions = { hideNonVisible: true, reposLabels: false}
	) {
	//console.log("updateDrawing");
	
	g_tooltipControl.resetObjMgr();	//???
	
	// clear canvas
	lay.canvasClear();
	
	lay.canvasCallCtx( "save" );
	lay.canvasCallCtx( "translate", g_lay.canvas.margin.left, 0);


	// Update Y Axis
	yAxisRedraw();

	// Update life lines
	updatePartLifeLines()
	
	// Update Boxes 
	updateBoxes( traceData.boxes, updateOptions );

	// Update msg Lines
	updateMsgLines( traceData.msgLines, updateOptions );
	
	// Update labels 
	updateLabels( traceData.labels, updateOptions );
	// Update Ann lines 
	updateAnnLines( traceData.annLines, updateOptions );

	lay.canvasCallCtx( "restore" );
	
	lay.scrollDummyUpdate();
	g_timeScaleControl.setSliderValue(lay.scaling.scaleFactor);
}
 



//-----------------------------------------------------------------------------
// Time scaling Controls
//


// Time scale control object 
function TimeScaleControl(lay, traceData) {
	var hasAnimFrameRequested = false;
	
	var mouseFlag = false;			// shift-mouse scale change in progress
	var mouseStartY = undefined;	// mouse Y at beginning of scaling progress
	var startScale = undefined; 	// scale at beginning of scaling progress 
	
	var requestedScale = undefined;	// current requested scale factor
	var zoomCenterY = undefined;
	var that = this;

	// key press events
	d3.select("body").on("keydown", function() {
		var key = d3.event.key;

		//console.log( "key code %s", d3.event.key );
		if( (key == '+' || key == '-')  )
			that.setPlusMinus( key );
	});
		
	// slider event
	d3.select("#ScaleSlider").on("input", function() {
    	var sliderValue = this.value;
    	var newscale = Math.pow(10, sliderValue);
    	
    	let bcr = this.getBoundingClientRect();
    	let midY = bcr.y + bcr.height/2;
    	
    	//console.log("slider changed", newscale);
		that.setTimeScale(newscale, midY);
    	
	})
	
	this.setSliderValue = function( scaleFactor ){
    	d3.select("#T-Scale").text(d3.format(".2f")(scaleFactor));
    	d3.select("#ScaleSlider").node().value = Math.log10(scaleFactor);
	}

	// if window big enough, position the slider next to the drawing, else
	// position slider on the right
	this.positionSlider = function(){
		let left = Math.min(lay.canvas.left + lay.canvas.fullWidth);
		let rightMargin = 70;
		
		left = Math.min(left, window.innerWidth - rightMargin);
		
		d3.select("#controls").style("left", left+"px");
		
	}
	
	// Callback for mousemove event. 
	// Support time scale changing by SHIFT+Mousemove
	this.mouseMove = function(e) {
		//console.log("mmZoom %f time=%f us", e.clientY, lay.screenY2Time(e.clientY) );
		if (e.shiftKey){
			if (mouseFlag === false){
				mouseStartY = e.clientY;
				mouseFlag = true;
				startScale = lay.scaling.scaleFactor; 
			}
			
			var newscale = startScale * Math.pow(1.02, (e.clientY - mouseStartY));
			//console.log( "mm newscale %f", newscale)
			that.setTimeScale(newscale, mouseStartY);
		}
		else mouseFlag = false;
	}
	
	// Change the time scale relative
	// @param direction "+" (zoom in) / "-" (zoom out)
	this.setPlusMinus = function( direction ){
		var mod = 0, newScale;
		
		switch( direction ){
		case '+':
			mod = 1.1;
			break;
		case '-':
			mod = 1/1.1;
			break;
		default:
			throw "bad direction " + direction;
		}

		// if animation already running, use last requested scaling factor
		if( ! hasAnimFrameRequested)
			newScale = lay.scaling.scaleFactor;
		else
			newScale = requestedScale;
		
		this.setTimeScale(newScale * mod, visualViewPortHeight()/2);	//??? 
		
	}

	
	// Change the time scale, do update decoupled via requestAnmiationFrame 
	// @param scale the new scale (1.0=original scale)
	// @param screenZoomY zoom around this y screen position 
	this.setTimeScale = function( scaleFactor, screenZoomY){
		if( scaleFactor > 0.01 && scaleFactor < 100){ //???
			
			requestedScale = scaleFactor;
			zoomCenterY = screenZoomY
			console.debug("setTimeScale %f %f", scaleFactor, screenZoomY, hasAnimFrameRequested);
			if( ! hasAnimFrameRequested){
				hasAnimFrameRequested = true;
				
				window.requestAnimationFrame(function() {
					that.draw();
			    });
			}
		}	
	}
	
	// callback for requestAnmiationFrame
	this.draw = function(){
		var timeZoomY, sceneYBeforeChange, sceneYAfterChange, scrollDelta;
		
		timeZoomY = lay.screenY2Time(zoomCenterY); 
		sceneYBeforeChange = lay.scaling.yScale(timeZoomY);
		let sceneHeightBeforeChange = lay.scaling.sceneHeight;
		// change scaling
		lay.sceneChangeTimeScale(requestedScale);
		
		// compute the Y position of the zoomCenter would be after scaling
		sceneYAfterChange = lay.scaling.yScale(timeZoomY);
		scrollDelta = sceneYAfterChange - sceneYBeforeChange;

		console.debug("tsdraw factor " + requestedScale);
		console.debug(" tsdraw yz " + zoomCenterY + "/" + lay.screen2CanvasY(zoomCenterY) + " t " + timeZoomY + " yac " + sceneYAfterChange + " sd " + scrollDelta + " scrollY " + window.scrollY);
		if( Math.floor(scrollDelta) != 0 && 
				(sceneHeightBeforeChange > lay.canvas.height) && 
				(window.scrollY+scrollDelta >= 0) &&
				(window.scrollY+scrollDelta < sceneHeightBeforeChange - lay.canvas.height)){
			//console.log(" draw scrollTo " + (window.scrollY+scrollDelta));
			window.scroll( window.scrollX, window.scrollY+scrollDelta);
		}
		else {
			updateDrawing(lay, traceData, { reposLabels: true });
			hasAnimFrameRequested = false;
			if( !this.redoSetTimeScale())
				requestedScale = undefined;
		}
			
	}

	this.scrollDone = function(){
		//console.log("scrolldone", requestedScale, lay.scaling.scaleFactor )
		hasAnimFrameRequested = false;
		this.redoSetTimeScale();
	}
	
	this.redoSetTimeScale = function(){
		if( requestedScale != undefined && requestedScale.toFixed(2) != lay.scaling.scaleFactor.toFixed(2) ){
			console.debug("redoSetTimeScale ", requestedScale, lay.scaling.scaleFactor)
			this.setTimeScale( requestedScale, zoomCenterY)
			return true;
		}
		return false;
	}
	
	window.addEventListener("mousemove", this.mouseMove);
	this.positionSlider();
}


//-------------------------------------------------------------------------------------
// Scroll/Zoom/Resize Handling
//
function WindowChangeControl(lay, timeScaleControl, traceData) {
	var hasAnimFrameRequested = false;
	var doResize = false;
	var that = this;
	var requestTimeOffset = undefined;
	
	this.scrolled = function(){
		requestTimeOffset = lay.y2Time(window.scrollY); 
		console.debug("scrolled ", window.scrollY, " ",  requestTimeOffset);
		
		that.requestAnim();
		// adjust horizontal position of parts and diagram div
		lay.setHorizontalScroll(window.scrollX);
	}
	
	this.zoomed = function(){
		//console.log("zoom ");
		doResize = true;
		that.requestAnim();
		timeScaleControl.positionSlider();
	}

	this.resized = function(){
		//console.log("resized");
		doResize = true;
		that.requestAnim();
		timeScaleControl.positionSlider();
	}

	this.requestAnim = function(){
		if( ! hasAnimFrameRequested ){
			hasAnimFrameRequested = true;
			requestAnimationFrame(that.draw);
		}
	}
	
	this.draw = function(){
		console.debug("wcDraw requestTimeOffset ", requestTimeOffset);
		if( requestTimeOffset !== undefined)
			lay.setTimeOffset(requestTimeOffset);
		
		if( doResize )
			lay.canvasResize();
		
	  	updateDrawing(lay, traceData, { reposLabels: true });
		
		hasAnimFrameRequested = false;
		timeScaleControl.scrollDone();
		doResize = false;
		requestTimeOffset = undefined;
	}

	window.addEventListener("resize", this.resized);
	window.addEventListener("zoom", this.zoomed);
	window.addEventListener("scroll", this.scrolled);
}


//-------------------------------------------------------------------------------------
// Tooltip control 
//

function TooltipControl(lay) {
	var that = this;
	var ctx = lay.canvas.mh.hidden.ctx;
	var activeObjNum; 				// currently tooltip'ed object, undefined if none
	var objIdx = undefined;
	var objs = [];
	const maxObjs = 1<<24;

	//Define the div for the label tooltip
	this.tooltipDiv = d3.select("body").append("div")	
	  .attr("class", "tooltip")				
	  .style("opacity", 0);

	
	// Callback for mousemove event. 
	this.mouseMove = function(e) {
		var canvasY = e.clientY - lay.canvas.top;
		var canvasX = e.clientX - lay.canvas.left + window.scrollX;
		
		if( canvasX > 0 && canvasY > 0 && canvasX < lay.canvas.fullWidth && canvasY < lay.canvas.height){
			let iData = ctx.getImageData( canvasX, canvasY, 1, 1).data;
			//console.log("mm x=%d y=%d cx=%d cy=%d data ", e.clientX, e.clientY, canvasX, canvasY, that.rgba2Num(iData)  );
			
			let objNum;
			if( (objNum = that.rgba2Num(iData)) != undefined ){
				let startToolTip = true;
				if( activeObjNum == undefined )
					activeObjNum = objNum;
				else if( activeObjNum != objNum)
					activeObjNum = objNum;
				else
					startToolTip = false;
				
				
				let text = objs[activeObjNum];
				if( startToolTip && text != undefined){
					that.tooltipStart( e.clientX + window.scrollX, e.clientY + window.scrollY, text);
					//console.log("TooltipStart ", text)
				}
			}
			else {
				// objNum is undefined
				if( activeObjNum != undefined ){
					that.tooltipEnd();
					//console.log("TooltipEnd ")
				}
				activeObjNum = undefined;
			}
			
		}
	}

	// Object management. The registered objects have to be drawn in the hidden canvas
	// with rgb values being the object index (alpha cannot be used as it is used for dithering)
	
	// reset the object index. must be called whenever the scene is redrawn
	this.resetObjMgr = function(){
		objIdx = 1;
		objs = [];
	}
	
	// register obj and return its rgb value (to be drawn into the hidden canvas)
	// @param obj: tooltip text
	// @return rgb value or undefined 
	this.registerObj = function( obj ){
		if( objIdx < maxObjs ){
			objs[objIdx] = obj;
			
			let rgb = numToRgbString(objIdx);
			objIdx++;
			return rgb;
		}
	}
	
	// convert rgba value from getImageData to the object number
	// value with alpha != 255 are ignored, these are dithering values
	// @iData: rgba image value (array with 4 entries)
	// @return object number or undefined
	this.rgba2Num = function( iData ){
		if( iData[3] == 255 ){
			return (iData[0]<<16) + (iData[1]<<8) + iData[2];  
		}
	}

	this.tooltipStart = function(x, y, text){
		that.tooltipDiv.transition()		
		.duration(200)		
		.style("opacity", .9);		
		that.tooltipDiv.html(text)	
		.style("left", (x) + "px")		
		.style("top", (y-20) + "px");
	}

	this.tooltipEnd = function(){
		that.tooltipDiv.transition()		
		.duration(500)		
		.style("opacity", 0);	
	}
	
	window.addEventListener("mousemove", this.mouseMove);
}

//--------------------------------------------------------------------------
//Helpers


function isUndefined(v){
	return v === undefined;
}


/**
 * From https://stackoverflow.com/questions/10962379/how-to-check-intersection-between-2-rotated-rectangles
 * Helper function to determine whether there is an intersection between the two polygons described
 * by the lists of vertices. Uses the Separating Axis Theorem
 *
 * @param a an array of connected points [{x:, y:}, {x:, y:},...] that form a closed polygon
 * @param b an array of connected points [{x:, y:}, {x:, y:},...] that form a closed polygon
 * @return true if there is any intersection between the 2 polygons, false otherwise
 */
function doPolygonsIntersect (a, b) {
    var polygons = [a, b];
    var minA, maxA, projected, i, i1, j, minB, maxB;

    for (i = 0; i < polygons.length; i++) {

        // for each polygon, look at each edge of the polygon, and determine if it separates
        // the two shapes
        var polygon = polygons[i];
        for (i1 = 0; i1 < polygon.length; i1++) {

            // grab 2 vertices to create an edge
            var i2 = (i1 + 1) % polygon.length;
            var p1 = polygon[i1];
            var p2 = polygon[i2];

            // find the line perpendicular to this edge
            var normal = { x: p2.y - p1.y, y: p1.x - p2.x };

            minA = maxA = undefined;
            // for each vertex in the first shape, project it onto the line perpendicular to the edge
            // and keep track of the min and max of these values
            for (j = 0; j < a.length; j++) {
                projected = normal.x * a[j].x + normal.y * a[j].y;
                if (isUndefined(minA) || projected < minA) {
                    minA = projected;
                }
                if (isUndefined(maxA) || projected > maxA) {
                    maxA = projected;
                }
            }

            // for each vertex in the second shape, project it onto the line perpendicular to the edge
            // and keep track of the min and max of these values
            minB = maxB = undefined;
            for (j = 0; j < b.length; j++) {
                projected = normal.x * b[j].x + normal.y * b[j].y;
                if (isUndefined(minB) || projected < minB) {
                    minB = projected;
                }
                if (isUndefined(maxB) || projected > maxB) {
                    maxB = projected;
                }
            }

            // if there is no overlap between the projects, the edge we are looking at separates the two
            // polygons, and we know there is no overlap
            if (maxA < minB || maxB < minA) {
                //CONSOLE("polygons don't intersect!");
                return false;
            }
        }
    }
    return true;
};

function rescaleCanvas(canvas) {
	  // finally query the various pixel ratios
	  let ctx = canvas.getContext('2d');

	  let devicePixelRatio = window.devicePixelRatio || 1;

	  let backingStoreRatio = ctx.webkitBackingStorePixelRatio ||
	                      ctx.mozBackingStorePixelRatio ||
	                      ctx.msBackingStorePixelRatio ||
	                      ctx.oBackingStorePixelRatio ||
	                      ctx.backingStorePixelRatio || 1;

	  let ratio = devicePixelRatio / backingStoreRatio;

	  //console.log("rescaleCanvas %f %f %f", devicePixelRatio, backingStoreRatio, ratio )
	  // upscale the canvas if the two ratios don't match
	  if (devicePixelRatio !== backingStoreRatio) {
	    let oldWidth = canvas.width;
	    let oldHeight = canvas.height;
	    canvas.width = oldWidth * ratio;
	    canvas.height = oldHeight * ratio;

	    canvas.style.width = oldWidth + 'px';
	    canvas.style.height = oldHeight + 'px';
	    // now scale the context to counter
	    // the fact that we've manually scaled
	    // our canvas element

	    ctx.scale(ratio, ratio);

	  }

}

function visualViewPortHeight(){
	//return window.document.documentElement.clientHeight;
	// visualViewport may work on chrome only!!!
	//return window.visualViewport.height;
	return d3.select("body").node().clientHeight;
}

//Converts from radians to degrees.
var degrees = function(radians) {
	return radians * 180 / Math.PI;
}
//Convert from degrees to radians
function radians(degrees)
{
	return degrees * (Math.PI/180);
}

/**-------------------------------------------------------------------------
* Rotate counterclockwise a point around a center point
* @param {Point} 	point 		point to rotate (Object with .x and .y members)
* @param {Point} 	center 		center point (Object with .x and .y members)
* @param {Float}	theta		angle to rotate (in radians, i.e. 2*PI=360 degrees) 
* 						 
* @return {Point}  rotated point
*/ 
function rotatePoint( point, center, theta ){
	// translate point to origin
	var tempX = point.x - center.x;
	var tempY = point.y - center.y;
	
	// now apply rotation
	var rotatedX = tempX * Math.cos(theta) - tempY * Math.sin(theta);
	var rotatedY = tempX * Math.sin(theta) + tempY * Math.cos(theta);
	
	// translate back
	var rv = {}
	rv.x = rotatedX + center.x;
	rv.y = rotatedY + center.y;
	return rv;
}

function numToRgbString( num ){
	let r = (num & 0x00ff0000) >> 16;
	let g = (num & 0x0000ff00) >> 8;
	let b = (num & 0x000000ff);
	
	return `rgb(
	  ${r}, 
	  ${g}, 
	  ${b} 
	  )`; 
}
