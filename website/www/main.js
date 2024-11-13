let my_name = "";
let socket = null;
let vjs_player = videojs("my-video", {
    controls: true,
    liveui: true,
    html5: {
        nativeTextTracks: false
    }
});

let html_player = document.getElementById("my-video_html5_api")

//let video_name_input = document.getElementById("video-name-input");
let video_select = document.getElementById("set-video-select")

let CURRENT_VIDEO = "";

//video_name_input.value = "";

let PRELOADING = false;
let PRELOAD_SEGMENTS_COUNT = 0;
let PRELOAD_TOTAL_SIZE_BYTES = 0;
let PRELOAD_TOTAL_SIZE_MB = 0;

function set_preloading_state(state) {
    let el = document.getElementById("preload-content");

    if (state) {
        el.textContent = "Stop preloading";
    } else {
        el.textContent = "Start preloading";
    }

    PRELOADING = state;
}

async function start_preloading() {
    set_preloading_state(true);

    let url = `videos/${CURRENT_VIDEO}/segments/video`;

    await preload_content(url);
    console.log("Preloading finished.");
    set_preloading_state(false);

}

function stop_preloading() {
    set_preloading_state(false);
}

async function preload_content(url) {
    let status = document.getElementById("preload-content-status");
    let speed = document.getElementById("preload-content-speed");

    return new Promise(async (resolve) => {
        let downloaded_size = 0;
        let downloaded_size_of_several_chunks = 0;

        let start_time = Date.now();

        let i = 0;
        while (PRELOADING) {
            if (i > PRELOAD_SEGMENTS_COUNT) {
                await new Promise(r => setTimeout(r, 1000));
                continue;
            }

            // console.log(`chunk ${i} started downloading.`);
            let segment_num = String(i).padStart(5, "0");

            // Cache video track
            let response = await fetch(`${url}/${segment_num}.m4s`);
            let data = await response.arrayBuffer();

            if (!response.headers.has('Cached-By-Worker')) {
                alert("Service worker is not working. Update the page or don't use preloading.");
                break;
            }

            downloaded_size += data.byteLength;
            downloaded_size_of_several_chunks += data.byteLength;

            // Cache audio track
            //response = await fetch(`${url}1-${segment_num}.m4s`);
            //data = await response.arrayBuffer();

            //console.log(`chunk ${i} downloaded. length => ${data.byteLength}`);

            let downloaded_size_str = Math.round(downloaded_size / 1024 / 1024);
            status.textContent = `${downloaded_size_str}/${PRELOAD_TOTAL_SIZE_MB} MB (${i}/${PRELOAD_SEGMENTS_COUNT} segments) (${Math.round(downloaded_size / PRELOAD_TOTAL_SIZE_BYTES * 100)}%)`;

	    // Date.now() returns milliseconds, not seconds.
            let time_spent = (Date.now() - start_time) / 1000;

            if (time_spent > 5) {
                let download_speed = (downloaded_size_of_several_chunks / time_spent / 1024 / 1024 * 8).toFixed(1); // Mbit

                speed.textContent = `${download_speed} Mbit/s`;

                start_time = Date.now();
                downloaded_size_of_several_chunks = 0;
            }

	    i += 1;
	}
        resolve();
    });
}

function send_pause_or_play_to_others()
{
    if (socket !== null && socket.readyState === socket.OPEN)
    {
        if (html_player.paused)
        {
            socket.send("pause;0");
        }
        else
        {
            socket.send("play;0");
        }
    }
}

function add_client_to_list(name, current_time, is_playing) {
    let new_client = document.createElement("div");
    new_client.className = "client-list-info";

    new_client.id = "client-list-" + name;

    if (my_name == name)
        new_client.style.backgroundColor = "rgb(60, 150, 60)";

    let client_name = document.createElement("p");
    let client_status = document.createElement("p");

    client_name.className = "client-list-info-entry";
    client_status.className = "client-list-info-entry";

    client_name.innerHTML = name;
    client_time = new Date(current_time * 1000).toISOString().substr(11, 8);

    if (is_playing == 0)
        client_status.innerHTML = `<span style=\"color: green; font-size: 30px;\">•<span style=\"color: white; font-size: 20px;\">${client_time}</span></span>`;
    else
        client_status.innerHTML = `<span style=\"color: red; font-size: 30px;\">•<span style=\"color: white; font-size: 20px;\">${client_time}</span></span>`;

    new_client.appendChild(client_name);
    new_client.appendChild(client_status);

    document.getElementById("client-list").appendChild(new_client);
}

function edit_client_in_list(name, current_time, is_playing) {
    let client = document.getElementById("client-list-" + name);

    let client_name = client.childNodes[0];
    let client_status = client.childNodes[1];
    let client_time = new Date(current_time * 1000).toISOString().substr(11, 8);

    if (client_name.innerHTML !== name)
        client_name.innerHTML = name;

    if (is_playing == 0)
        client_status.innerHTML = `<span style=\"color: green; font-size: 30px;\">•<span style=\"color: white; font-size: 20px;\">${client_time}</span></span>`;
    else
        client_status.innerHTML = `<span style=\"color: red; font-size: 30px;\">•<span style=\"color: white; font-size: 20px;\">${client_time}</span></span>`;
}

function connect_to_websocket_server()
{
    let new_socket = new WebSocket("wss://" + location.href.slice(8) + "websocket");

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
                if (html_player.paused)
                    html_player.play();
                break;

            case "pause":
                if (!html_player.paused)
                    html_player.pause();
                break;

            case "set_source":
                if (arg != "NOT_FOUND")
                {
                    console.log("Setting source to", arg);
                    vjs_player.src(arg);

                    CURRENT_VIDEO = arg.replace("videos/", "").replace("/master.m3u8", "");
                    video_select.value = CURRENT_VIDEO;

                    document.getElementById("preload-content").disabled = false;
                }
                else
                {
                    alert("Видео не существует. Попробуйте ещё раз.");
                }
                break;

            case "set_time":
                let current_time = Math.round(html_player.currentTime);
                let received_time = parseInt(arg);

                if (!html_player.paused && !(received_time - 3 <= current_time && current_time <= received_time + 3))
                    html_player.currentTime = arg;

                break;

            case "resync_time":
                html_player.currentTime = parseInt(arg);
                break;

            case "delete_client_info":
                let client = document.getElementById("client-list-" + arg);

                if (client != null)
                    client.remove();

                break;

            case "update_client_info":
                if (document.getElementById("client-list-" + split_data[1]) == null)
                    add_client_to_list(split_data[1], split_data[2], split_data[3]);
                else
                    edit_client_in_list(split_data[1], split_data[2], split_data[3]);
                break;

            case "client_name":
                my_name = arg;
                break;

            case "preload_info":
                PRELOAD_SEGMENTS_COUNT = parseInt(split_data[1]);
                PRELOAD_TOTAL_SIZE_BYTES = parseInt(split_data[2]);
                PRELOAD_TOTAL_SIZE_MB = Math.round(PRELOAD_TOTAL_SIZE_BYTES / 1024 / 1024)

                console.log(`Adjusting preload info. segments=${PRELOAD_SEGMENTS_COUNT} size=${PRELOAD_TOTAL_SIZE_MB}`)

                break;

            case "available_videos":
                for (let i = 1; i < split_data.length; i++) {
                    let option = document.createElement("option");

                    option.innerText = split_data[i];

                    video_select.appendChild(option);
                }

                video_select.value = CURRENT_VIDEO;

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
        socket.send("update_player_info;" + Math.round(html_player.currentTime) + ";" + (html_player.paused ? "1" : "0"))
}, 3000);

document.getElementsByClassName("vjs-progress-holder vjs-slider vjs-slider-horizontal")[0].onclick = function () {
    if (socket !== null && socket.readyState === socket.OPEN)
        socket.send("set_time;" + Math.round(html_player.currentTime))
};

document.getElementsByClassName("vjs-progress-control vjs-control")[0].onclick = function () {
    if (socket !== null && socket.readyState === socket.OPEN)
        socket.send("set_time;" + Math.round(html_player.currentTime))
};

document.getElementById("resync-time").onclick = function () {
    if (socket !== null && socket.readyState === socket.OPEN)
        socket.send("resync_time;0")
};

document.getElementById("preload-content").onclick = function () {
    set_preloading_state(!PRELOADING);
    if (PRELOADING) {
        start_preloading();
    } else {
        stop_preloading();
    }
};

html_player.onkeypress = function (e)
{
    if (e.which == 32)
    {
        if (html_player.paused)
        {
            if (socket !== null && socket.readyState === socket.OPEN)
            {
                socket.send("play;0");
                html_player.play();
            }
        }
        else
        {
            if (socket !== null && socket.readyState === socket.OPEN)
            {
                socket.send("pause;0");
                html_player.pause();
            }
        }
    }
};

video_select.onchange = function () {
    if (video_select.value != "")
    {
        if (socket !== null && socket.readyState === socket.OPEN)
            socket.send("set_source;" + video_select.value);
    }
};

/*document.getElementById("set-video-path").onclick = function () {
    if (video_name_input.value != "")
    {
        if (socket !== null && socket.readyState === socket.OPEN)
            socket.send("set_source;" + video_name_input.value);
    }
};*/

document.getElementById("reload-player").onclick = function () {
    vjs_player.src(`${CURRENT_VIDEO}/master.m3u8`);
};

html_player.onvolumechange = function() {
    localStorage.setItem('volume', html_player.volume);
};

html_player.onplay = function() {
    if (!html_player.seeking)
        socket.send("play;0");
};

html_player.onpause = function() {
    if (!html_player.seeking)
        socket.send("pause;0");
};

if (localStorage.getItem('volume') != null)
    html_player.volume = localStorage.getItem('volume')
