$(document).ready(function() {
  var count = -1;
  var prev = 0;
  var Config = null;
  
  $("div.friends li").live("click", function(evt) {
  
    if ($(this).hasClass("clicked")) {
      $(this).removeClass("clicked");
    } else {
      $(this).addClass("clicked");
    }
  
    count = count + 1;
    var el = count % 3;
    
    var img = "ul.choices div.choice" + el + " > img.usrimg";
    var name = "ul.choices div.choice" + el + " > input.text";
    var nusrid = "ul.choices div.choice" + el + " > input.usrid";
    
    var previd = $(nusrid).val();
    console.log("prev id : " + previd);
    if (previd != "") {
      $("div.friends li#" + previd).removeClass("clicked");
    }
    
    var usrimg = $(this).children("img.pic").attr("src");
    var ousrid = $(this).children("a.name").attr("userid");
    var usrname = $(this).children("a.name").attr("username");
    
    $(img).attr("src", usrimg);
    $(nusrid).val(ousrid);
    $(name).val(usrname).addClass("seltext");
  });
  
  $("div.invite input.awesome").live('click', function(evt) {
	FB.ui({ 
		method: "apprequests",
		title: "Who would you like to date this Valentine?",
		message: "Here is your chance to find a Valetine date in the safest way.\r\nPick 3 Valentines from your friends and if they pick you aswell then only both of you get to know that you chose each other.\r\n\r\nSo, What are you waiting for, Pick Your Valentine!",
		data: "tracking information for the user",
	});
  });
  
  $("div.welcome").click(function(){
    FB.login(function(response){
      if (!response.session) {
        alert("login failed");
      }
    }, {perms:'email,publish_stream'});
  });
  
  $("div.close-button").live("click", function(){
  	
  });
  
  $("form.picks input.awesome").click(function() {
		var validated = true;
	    $.each($("ul.choices div.choice"), function(i, child) { 
	    	if ($(child).find("input.text").val() == "" || $(child).find("input.usrid").val() == "") {
				validated = false;
	    	}
		});
		if (!validated) {
	    	$(".message .doops").fadeIn(800);
		} else {
			FB.ui({
			     method: 'feed',
			     name: username + " just made 3 picks from friends for a Valentine date.",
			     link: "http://apps.facebook.com/pickavalentine/",
			     picture: "http://pickavalentine.appspot.com/icon75x75.jpg",
			     caption: "Now " + username + " has a chance to find out if any of those 3 friends want to pick " + username + ". But the secret will only be revealed if the chosen friends also pick " + username + " ;)",
			     description: "So, what are you waiting for, Pick Your Valentine and discover who picks you back!",
			     message: ""
			   },
			   function(response) {
				   $("form.picks").submit();
					//     if (response && response.post_id) {
					//       alert('Post was published.');
					//     } else {
					//       alert('Post was not published.');
					//     }
			});
		}
	  return false;
  });
  
});

