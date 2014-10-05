(function ($) {
    function bootstrap_ui(container) {
        container = $(container);
        var prg_bar = $('<div class="progress-bar progress-bar-striped active">');
        var prg_display = $('<pre>Connecting...</pre>');
        var log_display = $('<pre>');

        container.html($('<div class="progress">').append(prg_bar));
        container.append(prg_display).append('<hr>').append(log_display);

        this.on('log_message', function (msg) {
            $('#logging').append(msg.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '\n').scrollTop(9999999);
        });
        this.on('progress', function (perc, text) {
            $('#master-pg').css({ width: (perc * 100) + '%' });
            $('#pg-well').text(text);

            log_display.height($(window).height() - log_display.offset().top - 50);
        });
        this.on('done', function (success) {
            prg_bar.removeClass('progress-bar-striped').removeClass('active');

            if(success) {
                prg_bar.addClass('progress-bar-success');
            } else {
                prg_bar.addClass('progress-bar-danger');
            }
        });

        log_display.height($(window).height() - log_display.offset().top - 50);
    }

    function Converter(url, ticket) {
        this.url = url;
        this.ticket = ticket;

        var _listeners = {};
        var _ws = null;
        var self = this;

        this.on = function (evt, cb) {
            if(!_listeners[evt]) {
                _listeners[evt] = [];
            }

            _listeners[evt].push(cb);
        };

        this.emit = function (evt, args) {
            $.each(_listeners[evt] || [], function (i, cb) {
                cb.apply(null, args);
            });
        };

        this.connect = function (ticket) {
            ticket = ticket || this.ticket;

            _ws = new WebSocket(url);
            _ws.addEventListener('open', function () {
                ws.send(ticket);
            });
            _ws.addEventListener('message', function (e) {
                var data = JSON.parse(e.data);

                self.emit(data[0], data.slice(1));
            });
        };

        this.bootstrap_ui = bootstrap_ui;
    }

    window.Converter = Converter;
})(jQuery);