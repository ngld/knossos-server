(function ($) {
    function update_tasks() {
        $.getJSON('/api/list_tasks', function (tasks) {
            var tbody = $('table tbody');
            var rows = $();

            if(tbody.length == 0) {
                tbody = $('<tbody>').appendTo('table');
            }

            tbody.empty();

            $.each(tasks, function (id, info) {
                var runtime = info.runtime;
                if(!runtime) {
                    runtime = new Date().getTime() / 1000 - info.time;
                }

                var row = $('<tr>').appendTo(tbody);
                row.append($('<td>').text(id));
                row.append($('<td>').text(info.state));
                row.append($('<td>').text(Math.round(runtime) + 's'));
                row.append($('<td>').text(new Date(info.time * 1000)));

                row.click(function () {
                    location.href = '/watch/' + id;
                });
            });

            setTimeout(update_tasks, 10000);
        });
    }

    $(function () {
        update_tasks();
    })
})(jQuery);