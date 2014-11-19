(function ($) {
    function bootstrap_ui(container, tpl) {
        var self = this;

        if(!tpl) {
            tpl = '<h4><span class="glyphicon glyphicon-cog"></span> Progress</h4>' +
                    '<hr>' +
                    '<div class="progress">' +
                    '    <div id="cv-pg-bar" class="progress-bar progress-bar-striped active" style="width: 0%;"></div>' +
                    '</div>' +
                    '<pre id="cv-pg-display">Initialising...</pre>' +
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
        this.on('captcha', function (image) {
            var win = $('<div>');
            win.css({
                position: 'fixed',
                top: '50%',
                left: '50%',
                'min-width': 400,
                background: 'white',
                border: '1px solid black',
                padding: '5px'
            });

            var form = $('<form>').appendTo(win);
            var img_el = $('<img>').attr('src', image);
            var input = $('<input type="text" class="form-control">');

            form.html('Please solve this captcha:<br>');
            form.append(img_el).append('<br>');
            form.append(input).append('<br><button type="submit" class="btn btn-primary">Send</button>');

            img_el.load(function () {
                win.css({
                    'margin-top': - (win.height() / 2),
                    'margin-left': - (win.width() / 2)
                });
            });

            form.submit(function (e) {
                e.preventDefault();
                self.send(input.val());
                win.remove();
            });

            $('body').append(win);
        })

        log_display.height($(window).height() - log_display.offset().top - 50);
    }

    function Converter(url, ticket) {
        TaskWatcher.apply(this, [url.replace('/ws/converter', '/ws/inter/' + ticket)]);
    }

    function TaskWatcher(url) {
        this.url = url;

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
            _ws.send(JSON.stringify([evt, [].slice.apply(arguments, [1])]));
        };

        this.connect = function () {
            var self = this;

            _ws = new WebSocket(this.url);
            _ws.addEventListener('open', function () {
                self.emit('user_ready');
            });
            _ws.addEventListener('message', function (e) {
                var data = JSON.parse(e.data);
                
                $.each(_listeners[data[0]] || [], function (i, cb) {
                    cb.apply(null, data[1]);
                });
            });
        };

        this.bootstrap_ui = bootstrap_ui;
    }

    window.Converter = Converter;
    window.TaskWatcher = TaskWatcher;
})(jQuery);