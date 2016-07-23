quit() {
    kill "$ws" "$server"
    wait
}

trap quit INT

if [ -d py-env ]; then
    source py-env/bin/activate
fi

python server.py &
server=$!

python websocket_server.py &
ws=$!

python worker.py &
worker=$!

wait