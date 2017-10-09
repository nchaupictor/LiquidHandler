function refreshData() {
      //alert("Calling refresh...");
      $.ajax({
        url: "/refresh",
        type: "GET",
        dataType: "json",
        success: function (data) {
          //alert("Refresh called. Result="+data.result);
          $("#time").html(data.time);
          $("#command").html(data.command);
          $("#incubationTime").html(data.incubationTime);
          $("#message").html(data.message);
          $("#submessage").html(data.submessage);
          $("#progressPercent").html(data.progressPercent);
          setTimeout(refreshData, 500);
        },
        error: function (xhr, status, err) {
          alert("Error: " + err);
        }
      });
    }

var temp = -1;
function updateProg() {
      $.getJSON('/progress', function (data) {
        progJ = data.progJ
        listCount = data.listC
        $("#progressPercent").css("width", progJ + '%').attr('aria-valuenow', progJ);

        //var temp = 0;       
          //Highlight list when progress percent reaches certain percentages
          //var lists = document.getElementsByClassName("list-group-item")[listCount];
          //lists.style.color = "#c7254e";
          console.log(listCount != temp && listCount != -1);
          if (listCount != temp && listCount > 0) {
            //for(i = 0 ; i < listCount; i ++){
              var lists = document.getElementsByClassName("list-group-item")[listCount - 1].innerHTML;
              var colorlists = document.getElementsByClassName("list-group-item")[listCount - 1];    
              var completed = lists.concat(String.fromCharCode(0x2714));
              colorlists.innerHTML = completed;
              colorlists.style.color = "#27b261";
              console.log("Colours changed!");
            //}
            temp = listCount;
          }     
      }); 
}

function tipCheck() {
      //jQuery.noConflict();
      $('#popup').modal({ show: false });
      $.getJSON('/refresh', function (data) {
        tipCount = data.tipCount
        if (tipCount == 12) {
          //$('#popup').modal('show');
          bootbox.alert('Modal popup');
          console.log("Modal shown");

          $('#tip').click(function () {
            $(this).removeClass('btn-danger').addClass('btn-success');
            $('#popup').modal('hide');
          });
        }
      });
}

function refreshCalib() {
            //alert("Calling refresh...");
            $.ajax({
                url: "/refreshCalib",
                type: "GET",
                dataType: "json",
                success: function (data) {
                    //alert("Refresh called. Result="+data.result);
                    $("#coordX").html(data.coordX);
                    $("#coordY").html(data.coordY);
                    $("#coordZ").html(data.coordZ);
                    $("#tipX").html(data.tipX);
                    $("#tipY").html(data.tipY);
                    $("#tipZ").html(data.tipZ);
                    $("#sampleX").html(data.sampleX);
                    $("#sampleY").html(data.sampleY);
                    $("#sampleZ").html(data.sampleZ);
                    $("#returnX").html(data.returnX);
                    $("#returnY").html(data.returnY);
                    $("#returnZ").html(data.returnZ);
                    $("#wasteTX").html(data.wasteTX);
                    $("#wasteTY").html(data.wasteTY);
                    $("#wasteTZ").html(data.wasteTZ);
                    $("#wasteLX").html(data.wasteLX);
                    $("#wasteLY").html(data.wasteLY);
                    $("#wasteLZ").html(data.wasteLZ);
                    $("#reserveX").html(data.reserveX);
                    $("#reserveY").html(data.reserveY);
                    $("#reserveZ").html(data.reserveZ);
                    $("#slideX").html(data.slideX);
                    $("#slideY").html(data.slideY);
                    $("#slideZ").html(data.slideZ);
                    setTimeout(refreshCalib, 1000);
                },
                error: function (xhr, status, err) {
                    alert("Error: " + err);
                }
            });
        }

        function activeTabf() {
            var activeTab = $('.nav-tabs .active').text()
            $.ajax({
                type: 'POST',
                url: "/activeTab",
                dataType: "text",
                data: { activeTab: activeTab },
                complete: setTimeout(function () { activeTabf() }, 2000),
                timeout: 1000
            });
        }

    function startProgram(){
      $("startButton").css({'background-color':"#21B6A8", "font-size": "105%"});
      $.ajax({
        type: 'POST',
        url: "/Start",
        dataType: "text",
        data:{startBool: 1}
      });
    }

      function skipProgram(){
      $.ajax({
        type: 'POST',
        url: "/Skip",
        dataType: "text",
        data:{startBool: 1}
      });
    }

      function stopProgram(){
      $.ajax({
        type: 'POST',
        url: "/Stop",
        dataType: "text",
        data:{startBool: 1}
      });
    }

          function moveHome(){
      $.ajax({
        type: 'POST',
        url: "/Home",
        dataType: "json"
      });
    }

          function moveLeft(){
      $.ajax({
        type: 'POST',
        url: "/Left",
        dataType: "text",
        data:{startBool: 1}
      });
    }

          function moveRight(){
      $.ajax({
        type: 'POST',
        url: "/Right",
        dataType: "text",
        data:{startBool: 1}
      });
    }

          function moveUp(){
      $.ajax({
        type: 'POST',
        url: "/Up",
        dataType: "text",
        data:{startBool: 1}
      });
    }

          function moveDown(){
      $.ajax({
        type: 'POST',
        url: "/Down",
        dataType: "text",
        data:{startBool: 1}
      });
    }

      function moveForward(){
      $.ajax({
        type: 'POST',
        url: "/Forward",
        dataType: "text",
        data:{startBool: 1}
      });
    }

          function moveBack(){
      $.ajax({
        type: 'POST',
        url: "/Backward",
        dataType: "text",
        data:{startBool: 1}
      });
    }

    
    function mapActivate(){
      var inArea,
            map = $("#layout")          
            captions = {
                SampleRack: ["Sample Rack", "Prepare 100 μL Serum Samples into the 0.2 mL 8-Well Strip Tubes labelled 1-8 and place into Sample Rack starting at Position 1 labelled on the Deck. This position correlates tothe first row of the first slide. After all the samples have been added, put the entire rack into the slot located on the layout map."],
                Reservoir: ["Reagent Reservoir", "Prepare 3 mL of Conjugate G, Conjugate M (if required), Detection Reagent, and Substrate Solution and 5 mL of Wash Buffer and dispense into their corresponding locations according to the labels on the Deck."],
                SlideTray: ["Slide Tray", "Place your PictArray™ Panel onto the Slide Tray, starting from the top-most position. Press down firmly onto the slide to ensure it is positioned properly. Place the entire tray onto the deck and also ensure it is positioned properly.  "],
                TipBox: ["96 Tip Box", "Place a 96 Well 200 μL Tip Box with lid removed into the corresponding Tip Box slot."],
                LiquidWaste: ["Liquid Waste", "Place a 50 mL Biotix Disposable Reagent Reservoir into the middle slot on the Deck."],
                TipWaste: ["Tip Waste", "Place the empty tip box into this slot"]

            },
            single_opts = {
                fillColor: 'f39c12',
                fillOpacity: 0.2,
                stroke: true,
                strokeColor: 'f39c12',
                strokeWidth: 10
            },
            //all_opts = {
                //fillColor: '000000',
                //fillOpacity: 0.6,
                //stroke: true,
                //strokeWidth: 2,
                //strokeColor: '0000ff'
            //}, 
            initial_opts = {
                mapKey: 'data-name',
                isSelectable: false,
                onMouseover: function (data) {
                    
                    inArea = true;
                    $('#layout-caption-header').text(captions[data.key][0]);
                    $('#layout-caption-text').text(captions[data.key][1]);
                    $('#layout-caption').show();
                },
                onMouseout: function (data) {
                    inArea = false;
                    $('#layout-caption').hide();
                }
            };
        opts = $.extend({},initial_opts, single_opts);

        map.mapster('unbind')
            .mapster(opts)
            .bind('mouseover', function () {
                if (!inArea) {
                    map.mapster('set_options', single_opts)
                       .mapster('set', true, 'all');
                }
            }).bind('mouseout', function () {
                if (!inArea) {
                    map.mapster('set', false, 'all');
                }
            });
    }
