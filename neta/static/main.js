$(document).ready(function() {
  $("div.friends li").live("click", function(evt) {
    if ($(this).hasClass("clicked")) {
      $(this).removeClass("clicked");
    } else {
      $(this).addClass("clicked");
    }
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
  
  $("form.picks input.awesome").click(function() {
  
	var fs = $("#jfmfs-container").data('jfmfs');
	var fi = fs.getSelectedIdsAndNames();
	
	var friends = "";
	var friend_ids = "";
	
	for (i = 0; i < fi.length; i++ ) {
		friends = friends + "" + fi[i].name + ";";
		friend_ids = friend_ids + "" + fi[i].id + ";";
		console.log("id: " + fi[i].id + ", name: " + fi[i].name); 
	}
	
	$("#friendlst").val(friends);
	$("#friendidlst").val(friend_ids);
	
	console.log("id: " + $("#friendidlst").val()); 
	console.log("names: " + $("#friendlst").val()); 
	
	if (fi.length == 0) {
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
//		   $("form.picks").submit();
	}
	return false;
  });
});
