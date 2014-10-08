(function ($) {
    function bootstrap_ui(container, tpl) {
        if(!tpl) {
            tpl = '<h4><span class="glyphicon glyphicon-cog"></span> Progress</h4>' +
                    '<hr>' +
                    '<div class="progress">' +
                    '    <div id="cv-pg-bar" class="progress-bar progress-bar-striped active" style="width: 0%;"></div>' +
                    '</div>' +
                    '<pre id="cv-pg-display"></pre>' +
                    '<br>' +
                    '<h4><span class="glyphicon glyphicon-list"></span> Log</h4>' +
                    '<hr>' +
                    '<pre id="cv-log"></pre>';
        }
        
        container = $(container).html(tpl);
        var prg_bar = container.find('#cv-pg-bar');
        var prg_display = container.find('#cv-pg-display');
        var log_display = container.find('#cv-log');

        this.on('log_message', function (msg) {
            log_display.append(msg.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '\n').scrollTop(9999999);
        });
        this.on('progress', function (perc, text) {
            prg_bar.css({ width: (perc * 100) + '%' });
            prg_display.text(text);

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
                _ws.send(ticket);
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