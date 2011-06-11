// Copyright 2010 Mike Brevoort http://mike.brevoort.com @mbrevoort
// 
// v1.0 jquery-facebook-multi-friend-selector
// 
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
// 
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
   
(function($) { 
    var JFMFS = function(element, options) {
        var elem = $(element),
            obj = this,
            uninitializedImagefriendElements = [], // for images that are initialized
            keyUpTimer,
            friends_per_row = 0,
            friend_height_px,
            first_element_offset_px;
            
        var settings = $.extend({
            max_selected: -1,
            max_selected_message: "{0} of {1} selected"
        }, options || {});
        var lastSelected;  // used when shift-click is performed to know where to start from to select multiple elements
                
        
        // ----------+----------+----------+----------+----------+----------+----------+
        // Initialization of container
        // ----------+----------+----------+----------+----------+----------+----------+
        elem.html(
            "<div id='jfmfs-friend-selector'>" +
//            "    <div id='jfmfs-inner-header'>" +
//            "        <span class='jfmfs-title'>Find Friends: </span><input type='text' id='jfmfs-friend-filter-text' value='pick a valentine'/>" +
//            "        <a class='filter-link selected' id='jfmfs-filter-all' href='#'>All</a>" +
//            "        <a class='filter-link' id='jfmfs-filter-selected' href='#'>Selected (<span id='jfmfs-selected-count'>0</span>)</a>" +
//            ((settings.max_selected > 0) ? "<div id='jfmfs-max-selected-wrapper'></div>" : "") +
//            "    </div>" +
            "    <div id='jfmfs-friend-container'></div>" +
            "</div>" 
        );
        
        var friend_container = $("#jfmfs-friend-container"),
            container = $("#jfmfs-friend-selector"),
            all_friends;
            
        FB.api('/me/friends?fields=id,name,gender', function(response) {
            var sortedFriendData = response.data.sort(function(a, b) {
                var x = a.name.toLowerCase();
                var y = b.name.toLowerCase();
                return ((x < y) ? -1 : ((x > y) ? 1 : 0));
            });
            
            var buffer = [];
            
            $.each(sortedFriendData, function(i, friend) {
//                buffer.push("<div class='jfmfs-friend' id='" + friend.id  +"'><img src='http://graph.facebook.com/" + friend.id + "/picture'/><div class='friend-name'>" + friend.name + "</div></div>");
            	buffer.push("<div class='jfmfs-friend' id='" + friend.id  +"'><img/><div class='friend-name'>" + friend.name + "</div></div>");
            });
            friend_container.append(buffer.join(""));
            
            uninitializedImagefriendElements = $(".jfmfs-friend", elem);
            uninitializedImagefriendElements.bind('inview', function (event, visible) {
                if( $(this).attr('src') === undefined) {
                    $("img", $(this)).attr("src", "//graph.facebook.com/" + this.id + "/picture");
                }
                $(this).unbind('inview');
            });

            init();
        });
        
        
        // ----------+----------+----------+----------+----------+----------+----------+
        // Public functions
        // ----------+----------+----------+----------+----------+----------+----------+
        
        this.getSelectedIds = function() {
            var ids = [];
            $.each(elem.find(".jfmfs-friend.selected"), function(i, friend) {
                ids.push($(friend).attr("id"));
            });
            return ids;
        };
        
        this.getSelectedIdsAndNames = function() {
            var selected = [];
            $.each(elem.find(".jfmfs-friend.selected"), function(i, friend) {
                selected.push( {id: $(friend).attr("id"), name: $(friend).find(".friend-name").text()});
            });
            return selected;
        };
        
        this.clearSelected = function () {
            all_friends.removeClass("selected");
        };
        
        // ----------+----------+----------+----------+----------+----------+----------+
        // Private functions
        // ----------+----------+----------+----------+----------+----------+----------+
        
        var init = function() {
            all_friends = $(".jfmfs-friend", elem);
            
            // calculate friends per row
            first_element_offset_px = all_friends.first().offset().top;
            for(var i=0, l=all_friends.length; i < l; i++ ) {
                if($(all_friends[i]).offset().top === first_element_offset_px) {
                    friends_per_row++;
                } else {
                    friend_height_px = $(all_friends[i]).offset().top - first_element_offset_px;
                    break;
                }
            }
            
            // handle when a friend is clicked for selection
            elem.delegate(".jfmfs-friend", 'click', function(event) {
                
              // if the element is being selected, test if the max number of items have
              // already been selected, if so, just return
//              if(!$(this).hasClass("selected") && maxSelectedEnabled() &&
//                $(".jfmfs-friend.selected").size() >= settings.max_selected && settings.max_selected != 1) {
//                     $(".message .oops").fadeIn(800);
//                     return;
//                }
                
                //hide oops!
//                $(".message .oops").fadeOut(800);
                
                //hide intro
//                $(".message .intro").fadeOut(800);
                    
                // if the max is 1 then unselect the current and select the new
                if(settings.max_selected == 1) {
                    elem.find(".selected").removeClass("selected");
                }
                
                // keep track of last selected, this is used for the shift-select functionality
                lastSelected = $(this);
                updateMaxSelectedMessage();
                
                elem.trigger("jfmfs.selection.changed", [obj.getSelectedIdsAndNames()]);
                
                var sel = this;
                var hasclass = $(this).hasClass("selected");
                
                if ( !hasclass ) {
                    $(this).addClass("selected");
                    var changed = false;
                    
                    $.each($("ul.choices div.choice"), function(i, child) { 
                        if ($(child).find("input.usrid").val() == "" && !changed) {
                            $(child).find("img.usrimg").attr("src", $(sel).find("img").attr("src"));
                            $(child).find("input.text").val( $(sel).find("div").text() ).addClass("seltext");
                            $(child).find("input.usrid").val( $(sel).attr("id") );
                            changed = true;
                        }
                     });
                } else {
                    $(this).removeClass("selected");
                    $.each($("ul.choices div.choice"), function(i, child) { 
                        if ($(child).find("input.usrid").val() == $(sel).attr("id")) {
                              $(child).find("img.usrimg").attr("src", "/girl.gif");
                            $(child).find("input.text").val( "pick a valentine" ).removeClass("seltext");
                            $(child).find("input.usrid").val( "" );
                        }
                     });
                }
                
                //friend selected, now show-all.
                all_friends.removeClass("hide-filtered");
                
                if ( $(".jfmfs-friend.selected").size() == settings.max_selected ) {
                  $(".message .doops").fadeOut(800);
                }
            });

//            // filter by selected, hide all non-selected
//            $("#jfmfs-filter-selected").click(function() {
//                all_friends.not(".selected").addClass("hide-non-selected");
//                $(".filter-link").removeClass("selected");
//                $(this).addClass("selected");
//            });
//
//            // remove filter, show all
//            $("#jfmfs-filter-all").click(function() {
//                all_friends.removeClass("hide-non-selected");
//                $(".filter-link").removeClass("selected");
//                $(this).addClass("selected");
//            });

            
            $(".close-button")
            	.live("click", function() {
		          	  var el = $(this).parent().parent();
		          	  $("div#jfmfs-friend-container div#" + $(el).find("input.usrid").val()).toggleClass("selected");
		          	  updateMaxSelectedMessage();
		          	  
		          	  $(el).find("input.usrid").val("");
		          	  $(el).find("img.usrimg").attr("src", "/girl.gif");
		          	  $(el).find("input.text").val("pick a valentine");
		          	  $(el).find("input.text").removeClass("seltext");
		          	  
	                  //hide oops!
	                  $(".message .oops").fadeOut(800);
            	});
            
            // filter as you type 
//            elem.find("#jfmfs-friend-filter-text")
            $(".friend-filter")
                .keyup( function() {
                    var filter = $(this).val();
                    clearTimeout(keyUpTimer);
                    keyUpTimer = setTimeout( function() {
                        if(filter == '') {
                            all_friends.removeClass("hide-filtered");
                            $.each($("ul.choices div.choice"), function(i, child) { 
                                if ($(child).find("input.text").val() == "") {
                                    //unselect the person!
                                    $("div#jfmfs-friend-container div#" + $(child).find("input.usrid").val()).toggleClass("selected");
                                    if( maxSelectedEnabled() ) {
                                        updateMaxSelectedMessage();
                                    }
                                    $(child).find("img.usrimg").attr("src", "/girl.gif");
                                    $(child).find("input.text").removeClass("seltext");
                                    $(child).find("input.usrid").val( "" );
                                    
                                    //hide oops!
                                    $(".message .oops").fadeOut(800);
                                    
                                }
                            });
                        } else {
                        	//hide intro by default
                            $(".message .intro").fadeOut(800);

                            container.find(".friend-name:not(:Contains(" + filter +"))").parent().addClass("hide-filtered");
                            container.find(".friend-name:Contains(" + filter +")").parent().removeClass("hide-filtered");
                            
                            var result = container.find(".friend-name:Contains(" + filter +")").parent();
//                            console.log("number of users " + result.size());
                            
                            if ( result.size() == 1) {
//                            	$(".message .doops").hide();
                            	$(".message .intro").fadeIn(800);
                            }
//                            	$(result).addClass("selected");
//                            	
//                            	console.log(" name " + $(result).find("div").text() + "," + $(this) );
//	                            $(this).val( $(result).find("div").text() ).addClass("seltext");
//	                            
//                            	console.log(" id " + $(result).attr("id") );
//	                            $(this).parent().parent().find("input.usrid").val( $(result).attr("id") );
//	                            
//                            	console.log(" img " + $(result).find("img").attr("src") );
//	                            $(this).parent().parent().find("img.usrimg").attr("src", $(result).find("img").attr("src"));
//	                        }
                            
                        }
                        showImagesInViewPort();
                    }, 200);
                })
                .focus( function() {
                    if($.trim($(this).val()) == 'pick a valentine') {
                        $(this).val('');
                    }
                })
                .blur(function() {
                    if($.trim($(this).val()) == '') {
                        $(this).val('pick a valentine');
                    }
                });

            // manages lazy loading of images
            var getViewportHeight = function() {
                var height = window.innerHeight; // Safari, Opera
                var mode = document.compatMode;

                if ( (mode || !$.support.boxModel) ) { // IE, Gecko
                    height = (mode == 'CSS1Compat') ?
                    document.documentElement.clientHeight : // Standards
                    document.body.clientHeight; // Quirks
                }

                return height;
            };
            
            var showImagesInViewPort = function() {
                var conteiner_height_px = friend_container.innerHeight(),
                    scroll_top_px = friend_container.scrollTop(),
                    container_offset_px = friend_container.offset().top,
                    $el, top_px,
                    elementVisitedCount = 0,
                    foundVisible = false;
                
                $.each(uninitializedImagefriendElements, function(i, $el){
                    elementVisitedCount++;
                    if($el !== null) {
                        $el = $( uninitializedImagefriendElements[i] );
                        top_px = (first_element_offset_px + (friend_height_px * Math.ceil(elementVisitedCount/friends_per_row))) - scroll_top_px - container_offset_px; 
                        if (top_px + friend_height_px >= -10 && 
                            top_px - friend_height_px < conteiner_height_px) {  // give some extra padding for broser differences
                                $el.data('inview', true);
                                $el.trigger('inview', [ true ]);
                                foundVisible = true;
                                uninitializedImagefriendElements[i] = null; 
                        } else {
                            if(foundVisible) {
                                return false;
                            }
                        }
                    }
                });
            };

            friend_container.bind('scroll', $.debounce( 250, showImagesInViewPort ));

            updateMaxSelectedMessage();
            showImagesInViewPort();
            elem.trigger("jfmfs.friendload.finished");
        };

        var selectedCount = function() {
            return $(".jfmfs-friend.selected").size();
        };

        var maxSelectedEnabled = function () {
            return settings.max_selected > 0;
        };
        
        var updateMaxSelectedMessage = function() {
            var message = settings.max_selected_message.replace("{0}", selectedCount()).replace("{1}", settings.max_selected);
            $("#jfmfs-max-selected-wrapper").html( message );
        };
    };
    
    $.fn.jfmfs = function(options) {
        return this.each(function() {
            var element = $(this);
            
            // Return early if this element already has a plugin instance
            if (element.data('jfmfs')) { return; }
            
            // pass options to plugin constructor
            var jfmfs = new JFMFS(this, options);
            
            // Store plugin object in this element's data
            element.data('jfmfs', jfmfs);
        });
    };
    
    // todo, make this more ambiguous
    jQuery.expr[':'].Contains = function(a, i, m) { 
        return jQuery(a).text().toUpperCase().indexOf(m[3].toUpperCase()) >= 0; 
    };
})(jQuery);

if($.debounce === undefined) {
    /*
     * jQuery throttle / debounce - v1.1 - 3/7/2010
     * http://benalman.com/projects/jquery-throttle-debounce-plugin/
     * 
     * Copyright (c) 2010 "Cowboy" Ben Alman
     * Dual licensed under the MIT and GPL licenses.
     * http://benalman.com/about/license/
     */
    (function(b,c){var $=b.jQuery||b.Cowboy||(b.Cowboy={}),a;$.throttle=a=function(e,f,j,i){var h,d=0;if(typeof f!=="boolean"){i=j;j=f;f=c}function g(){var o=this,m=+new Date()-d,n=arguments;function l(){d=+new Date();j.apply(o,n)}function k(){h=c}if(i&&!h){l()}h&&clearTimeout(h);if(i===c&&m>e){l()}else{if(f!==true){h=setTimeout(i?k:l,i===c?e-m:e)}}}if($.guid){g.guid=j.guid=j.guid||$.guid++}return g};$.debounce=function(d,e,f){return f===c?a(d,e,false):a(d,f,e!==false)}})(this);
}
