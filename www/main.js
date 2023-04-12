let socket = null;
let player = videojs("my-video", {
    controls: true,
    liveui: true
});

if (localStorage.getItem('videojs-volume') != null)
    player.volume(localStorage.getItem('videojs-volume'))

player.ready(() => {
    player.one('play', () => {document.getElementById("quality").onchange()});
});

player.on("volumechange", function() {
    localStorage.setItem('videojs-volume', player.volume());
});

player.on("play", function() {
    socket.send("play;0");
});

player.on("pause", function() {
    if (!player.seeking())
        socket.send("pause;0");
});

document.getElementById("quality").onchange = function () {
    value = document.getElementById("quality").value;
    localStorage.setItem('videojs-quality', value);

    if (value == "auto") {
        player.dash.mediaPlayer.updateSettings({streaming: {abr: {autoSwitchBitrate: {video: true}}}});
    } else {
        player.dash.mediaPlayer.updateSettings({streaming: {abr: {autoSwitchBitrate: {video: false}}}});
        player.dash.mediaPlayer.setQualityFor('video', value);
    }
};

document.getElementsByClassName("vjs-progress-holder vjs-slider vjs-slider-horizontal")[0].onclick = function () {
    if (socket !== null && socket.readyState === socket.OPEN)
        socket.send("set_time;" + Math.round(player.currentTime()))
};

document.getElementsByClassName("vjs-progress-control vjs-control")[0].onclick = function () {
    if (socket !== null && socket.readyState === socket.OPEN)
        socket.send("set_time;" + Math.round(player.currentTime()))
};

document.getElementById("resync-time").onclick = function () {
    if (socket !== null && socket.readyState === socket.OPEN)
        socket.send("resync_time;0")
};

document.getElementById("my-video_html5_api").onkeypress = function (e)
{
    if (e.which == 32)
    {
        if (player.paused())
        {
            if (socket !== null && socket.readyState === socket.OPEN)
            {
                socket.send("play;0");
                player.play();
            }
        }
        else
        {
            if (socket !== null && socket.readyState === socket.OPEN)
            {
                socket.send("pause;0");
                player.pause();
            }
        }
    }
};

let video_name_input = document.getElementById("video-name-input");
let video_name_label = document.getElementById("video-name-label")

video_name_input.value = "";

document.getElementById("set-video-path").onclick = function () {
    if (video_name_input.value != "")
    {
        if (socket !== null && socket.readyState === socket.OPEN)
            socket.send("set_source;" + video_name_input.value);
    }
};

function send_pause_or_play_to_others()
{
    if (socket !== null && socket.readyState === socket.OPEN)
    {
        if (player.paused())
        {
            socket.send("pause;0");
        }
        else
        {
            socket.send("play;0");
        }
    }
}

function connect_to_websocket_server()
{
    let new_socket = new WebSocket("ws://" + location.hostname + "/7787a1727d0f20e50e3f91f53aa1d2addae9e1fbe242c4262f32690f3220f14a/websocket");

    new_socket.onopen = function(e)
    {
        console.log("[WS] Соединение установлено");
    };

    new_socket.onmessage = function(event)
    {
        let split_data = event.data.split(';');
        let cmd = split_data[0];
        let arg = split_data[1];

        // console.log(`[WS] Данные получены с сервера: ${event.data}`);

        switch (cmd)
        {
            case "play":
                if (player.paused())
                    player.play();
                break;

            case "pause":
                if (!player.paused())
                    player.pause();
                break;

            case "set_source":
                if (arg != "NOT_FOUND")
                {
                    document.getElementById("quality").textContent = "";

                    console.log("Setting source to", arg);

                    player.src(arg);

                    quality_levels = split_data[2].split(" ");

                    for (let i = 0; i < quality_levels.length + 1; i++) {
                        option = document.createElement("option");
                        if (i == quality_levels.length) {
                            option.value = "auto";
                            option.innerHTML = "auto";
                        } else {
                            option.value = i;
                            option.innerHTML = quality_levels[i];
                        }

                        saved_quality = localStorage.getItem('videojs-quality');
                        if (saved_quality != null && saved_quality == option.value)
                            option.selected = true;

                        document.getElementById("quality").appendChild(option);
                    };

                    player.ready(function() {
                        //player.hlsQualitySelector({displayCurrentQuality: true,});
                        document.getElementById("quality").onchange();
                    });
                    video_name_label.innerHTML = arg;
                }
                else
                {
                    alert("Видео не существует. Попробуйте ещё раз.");
                }
                break;

            case "set_time":
                let current_time = Math.round(player.currentTime());
                let received_time = parseInt(arg);

                if (!(received_time - 3 <= current_time && current_time <= received_time + 3))
                    player.currentTime(arg);

                break;

            case "resync_time":
                player.currentTime(arg);
                break;

            case "delete_client_info":
                let client = document.getElementById("client-list-" + arg);
                if (client != null)
                    client.remove();
                break;

            case "update_client_info":
                if (document.getElementById("client-list-" + split_data[1]) == null)
                {
                    let new_client = document.createElement("div");
                    new_client.id = "client-list-" + split_data[1];
                    new_client.style.backgroundColor = "rgb(60, 60, 60)";
                    new_client.style.color = "white";
                    new_client.style.textAlign = "end";
                    new_client.style.borderRadius = "10px";
                    new_client.style.marginBottom = "5px";

                    let new_ip = document.createElement("p");
                    let new_time = document.createElement("p");
                    let new_status = document.createElement("p");

                    new_ip.className = "client-list-info-entry";
                    new_time.className = "client-list-info-entry";
                    new_status.className = "client-list-info-entry";

                    new_ip.innerHTML = split_data[2];
                    new_time.innerHTML = new Date(split_data[3] * 1000).toISOString().substr(11, 8);;

                    if (split_data[4] == 0)
                        status.innerHTML = "<span style=\"color: green; font-size: 30px; vertical-align: middle;\">•</span>Playing";
                    else
                        status.innerHTML = "<span style=\"color: red; font-size: 30px; vertical-align: middle;\">•</span>Paused";

                    new_client.appendChild(new_ip);
                    new_client.appendChild(new_time);
                    new_client.appendChild(new_status);

                    document.getElementById("client-list").appendChild(new_client);
                }
                else
                {
                    let recv_client = document.getElementById("client-list-" + split_data[1]);

                    let recv_ip = recv_client.childNodes[0];
                    let recv_time = recv_client.childNodes[1];
                    let recv_status = recv_client.childNodes[2];

                    recv_ip.innerHTML = split_data[2];
                    recv_time.innerHTML = new Date(split_data[3] * 1000).toISOString().substr(11, 8);

                    if (split_data[4] == 0)
                        recv_status.innerHTML = "<span style=\"color: green; font-size: 30px; vertical-align: middle;\">•</span>Playing";
                    else
                        recv_status.innerHTML = "<span style=\"color: red; font-size: 30px; vertical-align: middle;\">•</span>Paused";
                }
                break;
        }
    };

    new_socket.onclose = function(event)
    {
        socket = null;

        if (event.wasClean)
        {
            console.log(`[WS] Соединение закрыто чисто, код=${event.code} причина=${event.reason}`);
        }
        else
        {
            console.log('[WS] Соединение прервано');
        }

        document.getElementById("client-list").childNodes.forEach(function (e) {
            e.remove()
        })
    };

    new_socket.onerror = function(error)
    {
        console.log(`[WS] ${error.message}`);
    };

    socket = new_socket;
}

const update_player_info_interval = setInterval(function() {
    if (socket === null)
        connect_to_websocket_server();

    if (socket !== null && socket.readyState === socket.OPEN)
        socket.send("update_player_info;" + Math.round(player.currentTime()) + ";" + (player.paused() ? "1" : "0"))
}, 1000);
