quit() {
    kill "$ws" "$server"
    wait
}

trap quit INT

source py-env/bin/activate

python server.py &
server=$!

python websocket_server.py &
ws=$!

python worker.py &
worker=$!

wait