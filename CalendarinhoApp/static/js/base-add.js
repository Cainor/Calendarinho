function AddLeave(){
    // Display by providing setting object
    Fnon.Dialogue.Danger({
        title:'Add Leave',
        message:leave_form,
        callback:(closer,html)=>{
            var options = {
                dataType: "json",
                cache: false,
                success: AjaxSucceeded,
                error: AjaxFailed
            };
            $('#leave_add').ajaxSubmit(options)
        }
    });
    function AjaxSucceeded(result) {
        Fnon.Hint.Success('Seccessful Operation',{
            callback:function(){
            },
            title:'Calendarinho',
            position:'center-top',
            animation:'slide-top',
        });
    }
    function AjaxFailed(result) {
        Fnon.Hint.Danger('Failed Operation',{
            callback:function(){
            },
            title:'Calendarinho',
            position:'center-top',
            animation:'slide-top',
        });
    }
}

function AddEngagement(){
    // Display by providing setting object
    Fnon.Dialogue.Danger({
        title:'Add Engagement',
        message:engagement_form,
        callback:(closer,html)=>{
            var options = {
                dataType: "json",
                cache: false,
                success: AjaxSucceeded,
                error: AjaxFailed
            };
            $('#engagement_add').ajaxSubmit(options)
        }
    });
    function AjaxSucceeded(result) {
        Fnon.Hint.Success('Seccessful Operation',{
            callback:function(){
            },
            title:'Calendarinho',
            position:'center-top',
            animation:'slide-top',
        });
    }
    function AjaxFailed(result) {
        Fnon.Hint.Danger('Failed Operation',{
            callback:function(){
            },
            title:'Calendarinho',
            position:'center-top',
            animation:'slide-top',
        });
    }
}

function AddClient(){
    // Display by providing setting object
    Fnon.Dialogue.Danger({
        title:'Add Client',
        message:client_form,
        callback:(closer,html)=>{
            var options = {
                dataType: "json",
                cache: false,
                success: AjaxSucceeded,
                error: AjaxFailed
            };
            $('#client_add').ajaxSubmit(options)
        }
    });
    function AjaxSucceeded(result) {
        Fnon.Hint.Success('Seccessful Operation',{
            callback:function(){
            },
            title:'Calendarinho',
            position:'center-top',
            animation:'slide-top',
        });
    }
    function AjaxFailed(result) {
        Fnon.Hint.Danger('Failed Operation',{
            callback:function(){
            },
            title:'Calendarinho',
            position:'center-top',
            animation:'slide-top',
        });
    }
}