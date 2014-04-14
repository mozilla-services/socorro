/*
 * timeago: a jQuery plugin, version: 0.9.3 (2011-01-21)
 * @requires jQuery v1.2.3 or later
 *
 * Timeago is a jQuery plugin that makes it easy to support automatically
 * updating fuzzy timestamps (e.g. "4 minutes ago" or "about 1 day ago").
 *
 * For usage and examples, visit:
 * http://timeago.yarp.com/
 *
 * Licensed under the MIT:
 * http://www.opensource.org/licenses/mit-license.php
 *
 * Copyright (c) 2008-2011, Ryan McGeary (ryanonjavascript -[at]- mcgeary [*dot*] org)
 */
(function(d){d.timeago=function(g){if(g instanceof Date){return a(g)}else{if(typeof g==="string"){return a(d.timeago.parse(g))}else{return a(d.timeago.datetime(g))}}};var f=d.timeago;d.extend(d.timeago,{settings:{refreshMillis:60000,allowFuture:false,strings:{prefixAgo:null,prefixFromNow:null,suffixAgo:"ago",suffixFromNow:"from now",seconds:"less than a minute",minute:"about a minute",minutes:"%d minutes",hour:"about an hour",hours:"about %d hours",day:"a day",days:"%d days",month:"about a month",months:"%d months",year:"about a year",years:"%d years",numbers:[]}},inWords:function(l){var m=this.settings.strings;var i=m.prefixAgo;var q=m.suffixAgo;if(this.settings.allowFuture){if(l<0){i=m.prefixFromNow;q=m.suffixFromNow}l=Math.abs(l)}var o=l/1000;var g=o/60;var n=g/60;var p=n/24;var j=p/365;function h(r,t){var s=d.isFunction(r)?r(t,l):r;var u=(m.numbers&&m.numbers[t])||t;return s.replace(/%d/i,u)}var k=o<45&&h(m.seconds,Math.round(o))||o<90&&h(m.minute,1)||g<45&&h(m.minutes,Math.round(g))||g<90&&h(m.hour,1)||n<24&&h(m.hours,Math.round(n))||n<48&&h(m.day,1)||p<30&&h(m.days,Math.floor(p))||p<60&&h(m.month,1)||p<365&&h(m.months,Math.floor(p/30))||j<2&&h(m.year,1)||h(m.years,Math.floor(j));return d.trim([i,k,q].join(" "))},parse:function(h){var g=d.trim(h);g=g.replace(/\.\d\d\d+/,"");g=g.replace(/-/,"/").replace(/-/,"/");g=g.replace(/T/," ").replace(/Z/," UTC");g=g.replace(/([\+\-]\d\d)\:?(\d\d)/," $1$2");return new Date(g)},datetime:function(h){var i=d(h).get(0).tagName.toLowerCase()==="time";var g=i?d(h).attr("datetime"):d(h).attr("title");return f.parse(g)}});d.fn.timeago=function(){var h=this;h.each(c);var g=f.settings;if(g.refreshMillis>0){setInterval(function(){h.each(c)},g.refreshMillis)}return h};function c(){var g=b(this);if(!isNaN(g.datetime)){d(this).text(a(g.datetime))}return this}function b(g){g=d(g);if(!g.data("timeago")){g.data("timeago",{datetime:f.datetime(g)});var h=d.trim(g.text());if(h.length>0){g.attr("title",h)}}return g.data("timeago")}function a(g){return f.inWords(e(g))}function e(g){return(new Date().getTime()-g.getTime())}document.createElement("abbr");document.createElement("time")}(jQuery));
