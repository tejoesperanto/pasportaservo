$(document).ready(function(){
    // Close messageVoteForIdeas
    if (window.localStorage) {
        if (localStorage.getItem("messageVoteForIdeas")) {
            $(".messageVoteForIdeas").remove();
        }

        $(".messageVoteForIdeas a.close").click(function(e) {
            localStorage.setItem("messageVoteForIdeas", "hide");
        });
    }
});
