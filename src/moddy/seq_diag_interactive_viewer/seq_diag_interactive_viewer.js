/**
 * Moddy sequence diagram interactive viewer
 * Author: klauspopp@gmx.de
 * License: GPLV2
 */

'use strict'

/*
 * TODO
 * Search text function
 * Support time range
 * 
 * 
 */
const g_viewerName = "moddy sd interactive viewer";
const g_version = "0.8";

//-----------------------------------------------------------------------------------
// Shape classes. Must appear in source code before their usage

//base class for drawing shapes
class Shape {
	constructor( objData ){
		this.objData = objData;
	}
	isVisible(visibleRange){
		return false;
	}
	draw(){
	}
}

class MsgLineShape extends Shape {
	constructor( objData){
		super(objData);
	}
	isVisible(visibleRange){
		let d = this.objData;
		return isShapeVisible( visibleRange, (d.tp=="T-EXP") ? d.t : d.b, d.t );
	}
	draw(){
		let d = this.objData;
		let from = {}, to = {};
		from.x = (d.tp=="T-EXP") ? g_lay.partCenterX(d.p)-50 : g_lay.partCenterX(d.p);
		from.y = g_lay.time2CanvasY((d.tp=="T-EXP") ? d.t : d.b);
		to.x = (d.tp=="T-EXP") ? g_lay.partCenterX(d.p) : g_lay.partCenterX(d.s);
		to.y = g_lay.time2CanvasY(d.t);
		this.drawMsgLine( g_lay.canvas.mh.main.ctx, from, to, 
				('c' in d) ? d.c : (d.tp=="T-EXP") ? 'blue':'black',
				d.l == "t" ? true : false);

	}

	drawMsgLine( ctx, from, to, color, lost ){
		
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
			var point = this.msgLineArrowHead( from, to, angle, arrowLen);
			ctx.lineTo( point.x, point.y );
			ctx.moveTo( to.x, to.y);
			point = this.msgLineArrowHead( from, to, -angle, arrowLen);
			ctx.lineTo( point.x, point.y );
		}
		else {
			// draw "x" at end of line
			const angle = 45;
			const arrowLen = 6;
			var point = this.msgLineArrowHead( from, to, angle, arrowLen);
			ctx.lineTo( point.x, point.y );
			point = this.msgLineArrowHead( from, to, angle+180, arrowLen);
			ctx.lineTo( point.x, point.y );
			ctx.moveTo( to.x, to.y);
			point = this.msgLineArrowHead( from, to, -angle, arrowLen);
			ctx.lineTo( point.x, point.y );
			point = this.msgLineArrowHead( from, to, -angle+180, arrowLen);
			ctx.lineTo( point.x, point.y );
			
		}
		ctx.stroke();
	}
	msgLineArrowHead( from, to, angle, length){
		var dx = to.x - from.x;
		var dy = to.y - from.y;
		var theta = Math.atan2(dy, dx);
		var rad = radians(angle);
		return { x: to.x - length * Math.cos(theta + rad), 
			     y: to.y - length * Math.sin(theta + rad)};
	}

} 

class BoxShape extends Shape {
	constructor( objData){
		super(objData);
	}
	isVisible(visibleRange){
		let d = this.objData;
		return isShapeVisible( visibleRange, d.b, d.t );
	}
	draw(){
		let d = this.objData;
		let from = {}, to = {};
		let strokeStyle = ('sc' in d) ? d.sc : 'orange';
		let fillStyle = ('fc' in d) ? d.fc : 'white';
		let width = (d.tp=="STA") ? g_diagramArgs.statusBoxWidth : g_diagramArgs.variableBoxWidth;
		let x = g_lay.partCenterX(d.p) - width/2;
		let y = g_lay.time2CanvasY(d.b);
		let height = g_lay.scaling.yScale(d.t - d.b);
		this.drawBox( g_lay.canvas.mh.main.ctx, x, y, width, height, strokeStyle, fillStyle);

		// draw box into hidden canvas, so that tooltip can identify status
		let rgb = g_tooltipControl.registerObj( d.txt );
		
		if( rgb != undefined)
			this.drawBox( g_lay.canvas.mh.hidden.ctx, x, y, width, height, undefined, rgb);

	}
	drawBox( ctx, x, y, width, height, strokeStyle, fillStyle ){
		ctx.fillStyle = fillStyle;
		ctx.fillRect( x, y, width, height);
		if( strokeStyle != undefined){
			ctx.lineWidth = 1;
			ctx.strokeStyle = strokeStyle;
			ctx.strokeRect( x, y, width, height);
		}
	}
}

class AnnLineShape extends Shape {
	constructor( objData){	// sdl
		super(objData);
	}
	isVisible(visibleRange){
		let d = this.objData;
		return isShapeVisible( visibleRange, d.refLine.y1, d.refLine.y2 );
	}
	draw(){
		let d = this.objData;
		let from = { x: d.xPos(d.targetPoint.p, d.targetPoint.xo), y: g_lay.time2CanvasY(d.targetPoint.y) };
		let to   = { x: d.getCurrentCenter().x - 1, y: d.getCurrentCenter().y - 4 };
		
		this.drawAnnLine( g_lay.canvas.mh.main.ctx, from, to, d.color );
	}
	drawAnnLine( ctx, from, to, color ){
		ctx.save();
		ctx.beginPath();
		ctx.strokeStyle = color;
		ctx.lineWidth = 0.5;
		ctx.moveTo( from.x, from.y);
		ctx.lineTo( to.x, to.y);
		ctx.stroke();
		ctx.restore();
	}
}

class LabelShape extends Shape {
	constructor( objData){	// sdl
		super(objData);
	}
	isVisible(visibleRange){
		let d = this.objData;
		if(d === undefined) return false;
		return isShapeVisible( visibleRange, d.refLine.y1, d.refLine.y2 );
	}
	draw(ctx){
		let d = this.objData;

		// just for debugging 
		//drawLabelPolygon( g_lay.canvas.mh.main.ctx, d.getCurrentTextPolygon(), "pink"); 
		//drawLabelPolygon( g_lay.canvas.mh.main.ctx, d.getCurrentRefLinePolygon(), "pink");
		
		let searchHit = d.getSearchHit();
		if( searchHit.hit ){
			let color = d.color=="yellow" ? "black" : "yellow";
			if( searchHit.selected ) color = d.color=="orange" ? "black" : "orange";
			this.drawLabelPolygon( g_lay.canvas.mh.main.ctx, d.getCurrentTextPolygon(), color);
		}
		
		this.drawLabel( g_lay.canvas.mh.main.ctx, 
				d.getText(),
				d.getCurrentCenter(),
				d.getAnchor(),
				d.getCurrentRotation(),
				d.color);
		// draw label polygon into hidden canvas, so that tooltip can identify label
		let rgb = g_tooltipControl.registerObj( d.fullText );
		
		if( rgb != undefined)
			this.drawLabelPolygon( g_lay.canvas.mh.hidden.ctx, d.getCurrentTextPolygon(), rgb);
	}
	
	drawLabel(ctx, text, anchorPoint, textAlign, rotation, fillStyle){
		
		ctx.save();
		ctx.translate(anchorPoint.x, anchorPoint.y);
		ctx.rotate( rotation );
		ctx.textAlign = textAlign;
		ctx.fillStyle = fillStyle;
		ctx.fillText( text, 0, 0);
		ctx.restore();
	}
	drawLabelPolygon( ctx, polygon, fillStyle ){
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
}

class MarkerLineShape extends Shape {
	constructor( objData){	
		super(objData);
	}
	isVisible(visibleRange){
		let markerLine = this.objData;
		return markerLine.isActive && isShapeVisible( visibleRange, markerLine.time, markerLine.time );
	}
	draw(ctx){
		let markerLine = this.objData;
		let canvasWidth = g_lay.canvas.fullWidth;
		const maxTextWidth = 100;
		
		let drawPosition = g_lay.time2CanvasY(markerLine.time);

		// draw visible line
		this.drawMarker(g_lay.canvas.mh.main.ctx, markerLine.color, 1, 0, canvasWidth, drawPosition );
		
		// draw hidden line for tooltip
		let rgb = g_tooltipControl.registerObj( markerLine.sdl.fullText );
		if( rgb != undefined) {
			this.drawMarker(g_lay.canvas.mh.hidden.ctx, rgb, 10, 0, canvasWidth, drawPosition );
		}
	}
	
	drawMarker( ctx, color, width, x1, x2, y){
		ctx.beginPath();
		ctx.lineWidth = width;
		ctx.strokeStyle = color;
		ctx.moveTo( x1, y);
		ctx.lineTo( x2, y);
		ctx.stroke();
	}
}
//---------------------------------------------------------------------------------------------------
// STARTUP
// 

var g_diagramArgs = getDiagramArgs( g_moddyDiagramArgs );
var g_lay = new DrawingLayout(g_moddyDiagramParts, g_moddyTracedEvents);
var g_tooltipControl = new TooltipControl(g_lay);
  
let drawObjs = distributeTraceData(g_moddyTracedEvents);
let _shapes = drawObjs.shapes;
let _labels = drawObjs.labels;

let g_labelMgr = new LabelMgr(g_lay, _labels, 40 /*ms*/);

let g_markerLineManager = new MarkerLineManager(g_lay, g_labelMgr);
_shapes = _shapes.concat(g_markerLineManager.createShapes());

let g_drawingUpdateMgr = new DrawingUpdateMgr( g_lay, _shapes, g_labelMgr, 30 /*ms*/ );
let g_timeScaleControl = new TimeScaleControl(g_lay, g_drawingUpdateMgr);
let g_windowChangeControl = new WindowChangeControl(g_lay, g_timeScaleControl, g_drawingUpdateMgr);
let g_seachEngine = SearchEngine(g_lay, g_labelMgr, g_drawingUpdateMgr, 30 /*ms*/);

g_drawingUpdateMgr.requestParam({
	timeScale: g_lay.scaling.timeScale, 
	timeOffset: g_lay.scaling.timeOffset, 
	canvasFullWidth: g_lay.canvas.fullWidth,
	canvasHeight: g_lay.canvas.height,
	});

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
			hidden : { },				// hidden canvas d3 object and ctx
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
			left: 120				// X-offset to begin of drawing area
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
	this.modifyPartCenterToRight = function( idx, dx){
		
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
	
	// 
	this.modifyPartCenterDistance = function( idx, dx){
		
		let leftLimit = (idx == 0) ? 50 : partArray[idx-1].centerX + 50;
		
		if( idx > 0 && partArray[idx].centerX + dx >= leftLimit){
			let baseDx = idx==0 ? dx : dx/idx
					
			
			for( let i=1; i < partArray.length; i++){
				let part = partArray[i];
				part.centerX += baseDx * i;
			}
			
			this.setLogicalCanvasWidth( partArray.slice(-1)[0].centerX + this.spacingAfterLastPart() )
			return true;
		}
		return false;
	}
	this.partCenterX = function( partNo ){
		if (partNo == -1)
			return 0;	// "global" part 
		if (partNo === undefined || partNo >= partArray.length)
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
		if (d3.event.sourceEvent.shiftKey){
			that.modifyPartCenterDistance( i, dx );					// update distance between all parts
		} else {
			that.modifyPartCenterToRight( i, dx );					// update part and all parts on the right
		}
		that.updatePartBoxes();
		g_drawingUpdateMgr.requestParam({ canvasFullWidth: that.canvas.fullWidth });
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
	
	this.canvasResize = function (){	//TODO: pass parameters
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
		var height = this.scaling.sceneHeight + this.canvas.top + 50/*add some bottom space*/;
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
	
	/// TITLE bar
	this.initTitle = function(){
		let titleDiv = d3.select("body").select("#title");
		
		titleDiv.append("div")
			.style("float", "left")
			.style("padding-left", "20px")
			.append("p")
			.html(g_diagramArgs.title == "" ? "(Untitled)" : g_diagramArgs.title);

		
		// search input 
		let searchDiv = titleDiv.append("div")
		.style("float", "left")
		.style("margin-left", "20px")
	    .attr("id","SearchContainer")
	    .attr("spellcheck","false")
		
		searchDiv.append("p")
		 .html("Search: ")
		 .attr("class","SearchLabel")
		 .style("float", "left")
		searchDiv.append("input")
		 .attr("id","SearchInput")
		 .attr("type","text")
		searchDiv.append("p")
		 .attr("id","SearchResults")
		 .attr("class","SearchLabel")
		 .style("width","100px")
		 .html("")
		searchDiv.append("button")
		 .attr("class", "searchbutton")
		 .attr("id","SearchClear")
		 .html("x"/*\u2715"*/)
		searchDiv.append("button")
		 .attr("class", "searchbutton")
		 .attr("id","SearchNext")
		 .html("\u21E9")
		searchDiv.append("button")
		 .attr("class", "searchbutton")
		 .attr("id","SearchPrev")
		 .html("\u21E7")

		
		
		// markerLine time delta display 
		titleDiv.append("div")
			.style("float", "left")
			.style("margin-left", "20px")
			.append("p").attr("id","TimeMarkerDelta")

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

function yAxisRedraw()
{
	var timerange = g_lay.getVisibleTimeRange();
	var steps = yAxisTickSteps();
	var t = Math.max(timerange.start - (timerange.start%steps), 0);
	
	for( ; t<=timerange.end; t+=steps){
		drawYAxisTick(g_lay.canvas.mh.main.ctx, g_lay.time2CanvasY(t), g_lay.canvas.width);
		drawYAxisText(g_lay.canvas.mh.main.ctx, t, steps, g_lay.time2CanvasY(t));
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

		function yAxisformatTickValue(time, steps)
		{
			var rv;
			var fmt = ".0f"
			if( steps >= 1.0) rv = d3.format(fmt)(time) + " s";	
			else if( steps >= 1E-3) rv = d3.format(fmt)(time*1E3) + " ms";	
			else if( steps >= 1E-6) rv = d3.format(fmt)(time*1E6) + " us";	
			else if( steps >= 1E-9) rv = d3.format(fmt)(time*1E9) + " ns";
			else /*if( steps >= 1E-12)*/ rv = d3.format(fmt)(time*1E12) + " ps";
			return rv;
		}
	}
	function yAxisTickSteps(){
		var divPx = 60; 	
		
		var timeUnitsPerDiv = g_lay.scaling.maxTs/g_lay.scaling.sceneHeight*divPx;	// How much time in one div
		var logTuPerDiv = Math.log10(timeUnitsPerDiv);
		var floorlogTuPerDiv = Math.floor(logTuPerDiv);
		var rv;
		
		if( logTuPerDiv > (floorlogTuPerDiv + Math.log10(5)))
			rv = Math.pow(10,floorlogTuPerDiv) * 5;
		else if( logTuPerDiv > (floorlogTuPerDiv + Math.log10(2)))
			rv = Math.pow(10,floorlogTuPerDiv) * 2;
		else
			rv = Math.pow(10,floorlogTuPerDiv);
		//console.log ("yAxisTickSteps %f timeUnitsPerDiv %.3f logTuPerDiv %.3f ",  rv, timeUnitsPerDiv, logTuPerDiv);
		return rv;
		
	}

}


  
//---------------------------------------------------------------------------------
// Parse moddy trace data
// Create from allEvents the drawing shape objects and the SdLabel Objects
function distributeTraceData(allEvents){
	let shapes = { msgLines:[], boxes:[], annLines:[], labels:[]};
	let labels = [];
	
	for( let e of allEvents){
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
			color = e.tp == "ANN" ? "red" : "purple";
			anchor="start";
			targetPoint = {p: e.p, xo: 0, y: e.t}
			allowBelowLine = true;
			break;
		}
		if( 'c' in e)
			color = e.c;
		
		var sdl = new SdLabel( refLine, anchor, e.txt, color, g_lay, targetPoint, allowBelowLine );
		labels.push( sdl );

		shapes.labels.push(new LabelShape(sdl));
		
		switch(e.tp){
		case "<MSG":
		case "T-EXP":
			shapes.msgLines.push(new MsgLineShape(e));
			break;
		case "STA":
		case "VC":
			shapes.boxes.push(new BoxShape(e));
			break;
		case "ANN":
		case "ASSFAIL":
			shapes.annLines.push(new AnnLineShape(sdl));
			break;
		}

	}
	// combine all shapes into one array. Draw boxes first, annLines last
	let allShapes = shapes.boxes.concat(shapes.msgLines).concat(shapes.labels).concat(shapes.annLines);
	return { shapes: allShapes, labels: labels}
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
	
	this.searchHit = {};
	
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
	
	
	/// Search function
	
	// Check if sdl fullText contains searchText
	// if so, 
	this.searchMatch = function( searchText ){
		let hitStart = this.fullText.indexOf( searchText );
		if( hitStart !== -1 ){
			this.searchHit = { hit: true, selected: false, hitStart: hitStart, hitLength: searchText.length};
		}
		return hitStart !== -1;
	}
	
	this.searchSelect = function(){
		this.searchHit.selected = true;
	}
	
	this.searchSelectClear = function(){
		this.searchHit.selected = false;
	}

	this.searchClear = function(){
		this.searchHit = { hit: false, selected: false, hitStart: -1, hitLength: -1};
	} 
	
	this.getSearchHit = function(){
		return this.searchHit;
	}
	
	this.searchClear();
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
// Draw the part life lines
function updatePartLifeLines(){
	var visibleRange = g_lay.getVisibleTimeRange();
	var y0=g_lay.time2CanvasY(visibleRange.start);
	var y1=g_lay.time2CanvasY(visibleRange.end);
	
	for( let d of g_moddyDiagramParts){
		var from = { x: d.centerX, y: y0};
		var to 	 = { x: d.centerX, y: y1};
		
		drawLifeLine( g_lay.canvas.mh.main.ctx, from, to );
	}
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

}

//-----------------------------------------------------------------------------
// Label Manager
//
function LabelMgr( lay, labels, maxPlacementTime ) {
	
	this.positioningQ = new Queue();
	this.visibleLabels = [];
	
	this.getLabels = function(){
		return labels;
	}
	
	this.addLabel = function(sdl){
		console.debug("addLabel %s", sdl.fullText);
		labels.push(sdl);
	}
	
	this.removeLabel = function(sdl){
		let i;
		if((i=labels.indexOf(sdl)) !== -1){
			labels.splice(i, 1);
		}
	}
	
	// get array of currently visible labels
	// store array to this.visibleLabels
	this.computeVisibleLabels = function(){
		let visibleLabels = [];
		let visibleRange = lay.getVisibleTimeRange();	

		for( let sdl of labels ){
			if (isShapeVisible( visibleRange, sdl.refLine.y1, sdl.refLine.y2 )){
				sdl.resetPolygonCache();
				visibleLabels.push(sdl);
			}
		}
		
		this.visibleLabels = visibleLabels;	
		return visibleLabels;
	}
	
	// sceneChanged - to be called when the scene has changed in a way
	// that labels may have to be repositioned
	// 
	// adds all visible labels to the positioningQ, which are not already in Q
	this.sceneChanged = function(){
		this.computeVisibleLabels();
		
		for( let sdl of this.visibleLabels ){
			if( !this.positioningQ.includes( sdl )){
				this.positioningQ.push(sdl);
			}
		}
	}
	this.positioningQEmpty = function(){
		return this.positioningQ.length() == 0;		
	}

	// take labels out of the positioningQ, and perform autopositioning 
	// until max placement time is over.
	// @return: false if not all labels from Q could be positioned, true if so
	this.placeLabels = function(){
		
		let startTime = performance.now();
		let numPlacedLabels = 0;
		
		while(true){
			let sdl = this.positioningQ.shift();	// get label from positioningQ
			if( sdl == undefined )
				break;
			
			this.placeLabel(sdl);
			numPlacedLabels += 1;
			
			if( (numPlacedLabels > 2) && (performance.now() - startTime > maxPlacementTime) )
				break;
		}
		return this.positioningQEmpty();
	}

	
	// Place a single label
	this.placeLabel = function(sdl){
		let possiblyCollidingLabels = [];
		
		// make list of labels with which there might be a collision
		// use the reference line area for this check
		for( let otherLabel of this.visibleLabels )
			if( sdl.checkRefLinesMayCollide( otherLabel ))
				possiblyCollidingLabels.push(otherLabel);
		
		// virtually move around label to avoid overlapping text
		sdl.findBestPosition(possiblyCollidingLabels);
	}
	

}


//-----------------------------------------------------------------------------
// Time scaling Controls
//
function TimeScaleControl(lay, drawingUpdateMgr) {
	let mouseFlag = false;			// shift-mouse scale change in progress
	let mouseStartY = undefined;	// mouse Y at beginning of scaling progress
	let startScale = undefined; 	// scale at beginning of scaling progress 
	let that = this;

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
			
			let newscale = startScale * Math.pow(1.02, (e.clientY - mouseStartY));
			newscale = Math.max(0.01, newscale);
			newscale = Math.min(100, newscale);
			
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
		
		this.setTimeScale(lay.scaling.scaleFactor * mod, visualViewPortHeight()/2);	//??? 
		
	}

	
	// Change the time scale, do update decoupled via drawingMgr
	// @param scale the new scale (1.0=original scale)
	// @param screenZoomY zoom around this y screen position 
	this.setTimeScale = function( scaleFactor, screenZoomY){

		scaleFactor = Math.max(0.01, scaleFactor);
		scaleFactor = Math.min(100, scaleFactor);
		
		// determine which time is at screenZoomY
		let timeZoomY = Math.min(lay.screenY2Time(screenZoomY), lay.scaling.maxTs);	
		let curTimeSlice = timeZoomY - lay.scaling.timeOffset;
		let newTimeSlice = curTimeSlice * lay.scaling.scaleFactor / scaleFactor;
		let newTimeOffset = Math.max(timeZoomY - newTimeSlice, 0);
		
		console.debug( "setTimeScale timeZoomY %f curOffset %f newOffset %f", 
				timeZoomY, lay.scaling.timeOffset, newTimeOffset);
		
		drawingUpdateMgr.requestParam( {timeScale:scaleFactor, timeOffset:newTimeOffset} );
	}
	
	
	window.addEventListener("mousemove", this.mouseMove);
	this.positionSlider();
}


//-------------------------------------------------------------------------------------
// Scroll/Zoom/Resize Handling
//
function WindowChangeControl(lay, timeScaleControl, drawingUpdateMgr) {
	let that = this;
	let scrollMasked = false;
	let scrollMaskTimer;
	
	this.scrolled = function(){
		let timeOffset = lay.y2Time(window.scrollY); 

		// adjust horizontal position of parts and diagram div
		lay.setHorizontalScroll(window.scrollX);
		if( !scrollMasked ){
			console.debug("scrolled ", window.scrollY, " ",  timeOffset);
			drawingUpdateMgr.requestParam( {timeOffset} );
		}
	}
	
	this.zoomed = function(){
		let canvasHeight = visualViewPortHeight() - lay.canvas.top;
		drawingUpdateMgr.requestParam( {canvasHeight} );

		//console.log("zoom ");
		timeScaleControl.positionSlider();
	}

	this.resized = function(){
		that.zoomed();
	}
	
	function scrollMaskTimeout(){
		console.debug("scrollMaskTimeout");
		scrollMasked = false;
		scrollMaskTimer = undefined;
	}
	function scrollEventMaskCallback(){
		scrollMasked = true;
		if( scrollMaskTimer != undefined){
			window.clearTimeout(scrollMaskTimer);
		}
		scrollMaskTimer = window.setTimeout(scrollMaskTimeout, 500);
	}

	drawingUpdateMgr.setScrollEventMaskCallback(scrollEventMaskCallback);
	window.addEventListener("resize", this.resized);
	window.addEventListener("zoom", this.zoomed);
	window.addEventListener("scroll", this.scrolled);
}

//-----------------------------------------------------------------------------
// Marker Line manager
//
function MarkerLineManager(lay, labelMgr) {
	let that = this;
	
	// members of each markerline: 
	let markerLine = { 
		t1: { isActive:false, time:0, color:'green', sdl:undefined, labelShape:undefined}, 
		t2: { isActive:false, time:0, color:'red', sdl:undefined, labelShape:undefined}, 		
	};
	
	this.createShapes = function() {
		let shapes = [];
		
		shapes.push(new MarkerLineShape(markerLine.t1));
		shapes.push(new MarkerLineShape(markerLine.t2));
		markerLine.t1.labelShape = new LabelShape(undefined);
		markerLine.t2.labelShape = new LabelShape(undefined);
		shapes.push(markerLine.t1.labelShape);
		shapes.push(markerLine.t2.labelShape);
		return shapes;
	}
	
	function setActive( markerName, time ){
		let line = markerLine[markerName];
		let refLine = {}
		refLine.p1 = -1;
		refLine.xo1 = 0; //???
		refLine.p2 = undefined; // indicate rightmost position 
		refLine.xo2 = 0; 
		refLine.y1 = refLine.y2 = time;

		let sdl = new SdLabel( refLine, "start", markerFormatTime(time), line.color, g_lay, null, true);
		line.time = time;
		line.sdl = sdl;
		line.labelShape.objData = sdl;
		line.isActive = true;
		
		labelMgr.addLabel(sdl);
	} 
	function setInactive( markerName ){
		let line = markerLine[markerName];
		labelMgr.removeLabel(line.sdl);
		line.isActive = false;
		line.labelShape.objData = undefined;
	}
	
	function updateDelta(){
		let text;
		if(markerLine.t1.isActive && markerLine.t2.isActive){  
			text = "\u0394T: " + markerFormatTime(markerLine.t2.time - markerLine.t1.time);
		}
		else {
			text = "";
		}
		//console.debug("updateDelta %s", text)
		d3.select("#TimeMarkerDelta").node().textContent = text;
	}
	

	function markerFormatTime(time)
	{
		let rv;
		let fmt = ".4f"
		let absTime = Math.abs(time);
		if( absTime >= 1.0) rv = d3.format(fmt)(time) + " s";	
		else if( absTime >= 1E-3) rv = d3.format(fmt)(time*1E3) + " ms";	
		else if( absTime >= 1E-6) rv = d3.format(fmt)(time*1E6) + " us";	
		else if( absTime >= 1E-9) rv = d3.format(fmt)(time*1E9) + " ns";
		else if( absTime == 0) rv = "0";
		else /*if( absTime >= 1E-12)*/ rv = d3.format(fmt)(time*1E12) + " ps";
		return rv;
	}
	
	// Callback for mouseclick event: Set time markers
	this.mouseClick = function(e) {
		let line = {};
		let timerange = g_lay.getVisibleTimeRange();
		
		if( (e.clientX < g_lay.canvas.fullWidth) && (e.clientY > g_lay.canvas.top) && (e.which == 1 /* left mouse button*/) ) {
			var timeAtY = g_lay.screenY2Time(e.clientY);
			
			if( timeAtY <= timerange.end && timeAtY >= 0.0) {
				
				let markerName = e.ctrlKey ? "t2" : "t1";
				let line = markerLine[markerName];
				
				if(line.isActive){
					setInactive(markerName);
				}
				else {
					setActive(markerName, timeAtY);					
				}
				updateDelta();
				g_drawingUpdateMgr.requestParam( {doRedraw:true} );
			} 
		}
	}
	
	window.addEventListener("click", this.mouseClick);
}



//-------------------------------------------------------------------------------------
// Drawing update manager
//
function DrawingUpdateMgr(lay, shapes, labelMgr, maxShapeDrawTime){
	// these variables store the currently shown and the requested parameters:
	// timeScale, timeOffset, canvasFullWidth, canvasHeight 
	let shown = {};		 
	let requested = {};
	
	let animFrameRequested = false;
	let scrollEventMaskCallback;
	let redrawShapeIdx = 0;
	
	this.requestParam = function( params ){
		for( let param of Object.keys(params)){
			requested[param] = params[param]; 
		}
		checkAnimation();
	}
	
	function checkAnimation(){
		
		if( shown.timeScale != requested.timeScale ||
			shown.timeOffset != requested.timeOffset ||
			shown.canvasFullWidth != requested.canvasFullWidth ||
			shown.canvasHeight != requested.canvasHeight ||
			labelMgr.positioningQEmpty() == false ||
			redrawShapeIdx < shapes.length-1 ||
			requested.doRedraw == true){
			
			if( !animFrameRequested ){
				requestAnimationFrame(draw);
				animFrameRequested = true;
			}
		}
	}
	
	function draw(){
		let doCompleteRedraw = false;
		animFrameRequested = false;
		
		if( shown.timeScale != requested.timeScale ){
			// change scene time scale
			lay.sceneChangeTimeScale(requested.timeScale);
			
			// adjust the browsers scrollbar
			// disable temporarily scroll events 
			let scrollY = lay.scaling.yScale(requested.timeOffset);
			scrollEventMaskCallback();			
			window.scroll( window.scrollX, scrollY);
			console.debug( "draw: timeScaleChanged %f %f scrollTo %f/%d", 
					shown.timeScale, requested.timeScale, lay.y2Time(scrollY), scrollY);
			shown.timeScale = requested.timeScale;
			doCompleteRedraw = true;
		}
		
		if( shown.timeOffset != requested.timeOffset ){
			if( requested.setScrollY == true ){
				let scrollY = lay.scaling.yScale(requested.timeOffset);
				console.debug("draw: scrollToY %d", scrollY);
				window.scroll( window.scrollX, scrollY);
				requested.setScrollY = false;
			}
			
			console.debug("draw: timeOffset changed %f %f", shown.timeOffset, requested.timeOffset );
			if( lay.scaling.sceneHeight <= lay.canvas.height ){
				// The total scene fits into the visible area, it makes no sense to hide parts before timeoffset
				console.debug("draw: timeOffset forced to 0");
				requested.timeOffset = 0;
			}
				
			lay.setTimeOffset(requested.timeOffset);
			shown.timeOffset = requested.timeOffset;
			doCompleteRedraw = true;
		}

		if( shown.canvasFullWidth != requested.canvasFullWidth ||
			shown.canvasHeight != requested.canvasHeight){
			console.debug("draw: resize");
			//console.time('canvasResize');
			lay.canvasResize();
			//console.timeEnd('canvasResize');
			shown.canvasFullWidth = requested.canvasFullWidth;
			shown.canvasHeight = requested.canvasHeight;
			doCompleteRedraw = true;
		}
		if( requested.doRedraw == true ) {
			doCompleteRedraw = true;
			requested.doRedraw = false;
		}

		if( doCompleteRedraw ){
			labelMgr.sceneChanged();
			beginRedraw();
		}
		else {
			beginPartialDraw();
		}
		//console.debug("draw: labels in q %d", labelMgr.positioningQ.length());

		//console.time('labelMgrPlace');
		labelMgr.placeLabels();
		//console.timeEnd('labelMgrPlace');
		
		//console.time('drawShapes');
		drawShapes();
		//console.timeEnd('drawShapes');
		
		endRedraw();
		checkAnimation();
	}
	this.setScrollEventMaskCallback = function(cb){
		scrollEventMaskCallback = cb;
	}

	function beginRedraw(){
		g_tooltipControl.resetObjMgr();
		
		// clear canvas
		lay.canvasClear();
		
		beginPartialDraw();

		// Update Y Axis
		yAxisRedraw();

		// Update life lines
		updatePartLifeLines();
		
		redrawShapeIdx = 0;
	}
	
	function beginPartialDraw(){
		lay.canvasCallCtx( "save" );
		lay.canvasCallCtx( "translate", g_lay.canvas.margin.left, 0);
	}
	function drawShapes(){
		let startTime = performance.now();
		let numDrawnShapes = 0;
		let visibleRange = lay.getVisibleTimeRange();
		let shapeIdx;
		
		for( shapeIdx = redrawShapeIdx; shapeIdx < shapes.length; shapeIdx++){
			let shape = shapes[shapeIdx];
			if( shape.isVisible(visibleRange) ){
				shape.draw();
				numDrawnShapes += 1;
			}
			if( (numDrawnShapes > 10) && (performance.now() - startTime > maxShapeDrawTime) ){
				shapeIdx++;
				break;
			}
		}
		redrawShapeIdx = shapeIdx;
	}
	
	function endRedraw(){
		lay.canvasCallCtx( "restore" );
		
		lay.scrollDummyUpdate();
		g_timeScaleControl.setSliderValue(lay.scaling.scaleFactor);		
	}
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
	var markerLineActive = false;
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
			//console.debug("mm x=%d y=%d cx=%d cy=%d data ", e.clientX, e.clientY, canvasX, canvasY, that.rgba2Num(iData)  );
			
			// check if mouse is over label
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

	
	window.addEventListener("mousemove", this.mouseMove);
}


//--------------------------------------------------------------------------
// Text Search Engine

function SearchEngine(lay, labelMgr, drawingUpdateMgr, maxSearchTime) {
	let that = this;
	let foundLabels = [];
	let foundSelectedIdx = 0;
	let currentSearchText = "";
	let searchIdx;
	let animFrameRequested = false;
	let allLabelsCount;	// num labels when search started 
	
	function nextSearchResult(){
		console.log("nextSearchResult clicked");
		if( foundLabels.length > 0){
			
			if( foundSelectedIdx < foundLabels.length-1){
				changeSelectedIdx(foundSelectedIdx+1);
			}
			else {
				changeSelectedIdx(0);				
			}
		}
	}
	
	function prevSearchResult(){
		console.log("prevSearchResult clicked");
		if( foundLabels.length > 0){
			
			if( foundSelectedIdx > 0){
				changeSelectedIdx(foundSelectedIdx-1);
			}
			else {
				changeSelectedIdx(foundLabels.length-1);				
			}
		}
	}
	function clearSearch(){
		console.log("clearSearchResult clicked");
		searchTextInput.node().value = currentSearchText = "";
		clearLabels();
		changeSelectedIdx(-1);
	}
	function searchInputChanged(){
		let searchText = searchTextInput.node().value;
		
		if( searchText != currentSearchText && searchText != ""){
			currentSearchText = searchText;
			searchIdx = 0;
			clearLabels();
			changeSelectedIdx(-1);
			allLabelsCount = labelMgr.getLabels().length;
			
			console.debug("search start new search %s", searchText);
			if( !animFrameRequested ){
				requestAnimationFrame(deferredSearch);
				animFrameRequested = true;
				
			}
		}
		else if( searchText == "" ){
			currentSearchText = searchText;
			clearSearch();
		}
	}
	
	function deferredSearch(){
		animFrameRequested = false;
		
		if( currentSearchText != ""){
			let searchHitsBefore = foundLabels.length;
			searchIdx = doSearch( currentSearchText, searchIdx );
			let searchHitsAfter = foundLabels.length;
			
			if( searchHitsBefore != searchHitsAfter){
				changeSelectedIdx(foundLabels.length > 0 ? 0: -1);
			}
			
			if( searchIdx < allLabelsCount){
				console.debug("search deferred idx=%d %s", searchIdx, currentSearchText);
				requestAnimationFrame(deferredSearch);
				animFrameRequested = true;	
			}
			else {
				console.debug("search done idx=%d found %d", searchIdx, foundLabels.length);
			}
		}
		updateSearchResult();
	}
	
	function clearLabels(){
		for( let sdl of foundLabels){
			sdl.searchClear();
		}
		foundLabels = [];
	}
	
	function doSearch( searchText, startIdx ){
		let labelIdx = startIdx;
		let startTime = performance.now(); 
		let labels = labelMgr.getLabels();

		for( ; labelIdx < allLabelsCount; labelIdx++){
			let sdl = labels[labelIdx];
		
			if( sdl.searchMatch( searchText ) == true ){
				foundLabels.push(sdl);
				console.debug("searchhit: %s", sdl.fullText);
			}
			if( performance.now() - startTime > maxSearchTime ){
				labelIdx++;
				break;
			}
		}
		return labelIdx;
	}
	
	function changeSelectedIdx( newIdx ){
		let gotoTime = undefined;
		if( foundSelectedIdx >= 0 && foundSelectedIdx < foundLabels.length){
			foundLabels[foundSelectedIdx].searchSelectClear();
		}
		if( newIdx >= 0 && newIdx < foundLabels.length){
			let sdl = foundLabels[newIdx]; 
			sdl.searchSelect();
			
			// check if label is currently visible. If not, scroll so it will be visible
			if (isShapeVisible( lay.getVisibleTimeRange(), sdl.refLine.y1, sdl.refLine.y2 ) == false){
				gotoTime = (sdl.refLine.y1 + (sdl.refLine.y2 - sdl.refLine.y1) * sdl.hpos) - lay.y2Time( lay.canvas.height * 0.3);
				console.debug("gotoTime: %f", gotoTime);
			}
		}
		foundSelectedIdx = newIdx;
		redraw( gotoTime );
	}
	
	function updateSearchResult(){
		let text = "";
		let searchInProgress = (searchIdx < allLabelsCount);
		console.debug("searchIdx %d labels %d", searchIdx, allLabelsCount);
		if (foundSelectedIdx >= 0){
			text = (foundSelectedIdx+1).toString() + "/" + foundLabels.length.toString();
			if( searchInProgress) text += "?";
		}
		else if( currentSearchText != ""){
			text = searchInProgress ? "Searching" : "No Match";
		}
		searchResults.html( text );
	}
	function redraw( gotoTime ){
		updateSearchResult();
		let request = {doRedraw:true};
		if( gotoTime !== undefined ) request = {doRedraw:true, timeOffset:gotoTime, setScrollY:true};  
		drawingUpdateMgr.requestParam( request );		
	}
	let searchTextInput = d3.select("#SearchInput");
	searchTextInput.on("keyup", searchInputChanged);
	searchTextInput.on("change", searchInputChanged);
	searchTextInput.on("submit", searchInputChanged);
	let searchResults = d3.select("#SearchResults");
	d3.select("#SearchNext").on("click", nextSearchResult);
	d3.select("#SearchPrev").on("click", prevSearchResult);
	d3.select("#SearchClear").on("click", clearSearch);
	
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
    
    /*
    // different approach for testing polygon intersection
    // create bounding box around polygon and test box intersection
    var xMinA = 1000000, xMaxA = 0, yMinA = 1000000, yMaxA = 0; // bounding box of polygon a
    var xMinB = 1000000, xMaxB = 0, yMinB = 1000000, yMaxB = 0; // bounding box of polygon b
    
    var iA;
    var iB;
    
    // create bounding box of a
    for(iA = 0; iA < a.length; ++iA) {
    	if( a[iA].x < xMinA ) {
    		xMinA = a[iA].x;
    	}
    	if( a[iA].x > xMaxA ) {
    		xMaxA = a[iA].x;
    	}
    	if( a[iA].y < yMinA ) {
    		yMinA = a[iA].y;
    	}
    	if( a[iA].y > yMaxA ) {
    		yMaxA = a[iA].y;
    	}
    }
    
    // create bounding box of b
    for(iB = 0; iB < b.length; ++iB) {
    	if( b[iB].x < xMinB ) {
    		xMinB = b[iB].x;
    	}
    	if( b[iB].x > xMaxB ) {
    		xMaxB = b[iB].x;
    	}
    	if( b[iB].y < yMinB ) {
    		yMinB = b[iB].y;
    	}
    	if( b[iB].y > yMaxB ) {
    		yMaxB = b[iB].y;
    	}
    }
    
    // test intersection of boxes a and b
    if( (xMinA <= xMinB) && (xMinB <= xMaxA) || (xMinA <= xMaxB) && (xMaxB <= xMaxA) 
    		|| (xMinB <= xMinA) && (xMinA <= xMaxB) || (xMinB <= xMaxA) && (xMaxA <= xMaxB)) {
        if( (yMinB <= yMinA) && (yMinA <= yMaxB) || (yMinB <= yMaxA) && (yMaxA <= yMaxB) 
        		|| (yMinA <= yMinB) && (yMinB <= yMaxA) || (yMinA <= yMaxB) && (yMaxB <= yMaxA)) {
        	//console.log("intersect!");
        	//console.log(xMinA, xMaxA, yMinA, yMaxA);
            //console.log(xMinB, xMaxB, yMinB, yMaxB);
        	return true;
        } else {
        	return false;
        }
    } else {
    	return false;
    }
	*/
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


//----------------------------------------------------------------------------
// A Queue

function Queue() {
	this.elements = [];	// the queue elements
	
	//@param: variable number of objects to push to queue 
	this.push = function(){
		Array.prototype.push.apply( this.elements, Array.from(arguments));
	}
	
	//@param: arr Array of objects to push to queue 
	this.pushArray = function(arr){
		Array.prototype.push.apply( this.elements, arr);
	}
	// remove first element from queue
	//@return: first element in queue or undefined
	this.shift = function(){
		return this.elements.shift();
	}
	
	//@return: Number of elements in queue
	this.length = function(){
		return this.elements.length;
	}
	
	//test if elem is in queue
	//@return: true if so
	this.includes = function(elem){
		return this.elements.includes(elem);
	}
	
	this.elements = Array.from(arguments);	
};

