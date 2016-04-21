/*
    The reservation calendar extends fullcalendar adding methods to allocate
    dates, select and then reserve them.
*/

var rc = $.reservationCalendar = {};
var defaultOptions = {
    /*
        Returns the allocations in a fullcalendar compatible events feed.
        See http://fullcalendar.io/docs/event_data/events_json_feed/
    */
    feed: null,

    /*
        Returns the reservations for the current resource.
    */
    reservations: null,

    /*
        The type of the calendar. Either 'room' or 'daypass'
    */
    type: null,

    /*
        The visible time range
    */
    minTime: '07:00:00',
    maxTime: '22:00:00',

    /*
        True if the calendar may be edited (by editors/admins)
    */
    editable: false,

    /*
        Url called when a new selection is made. For example:

            selectUrl: https://example.org/on-select

        Will be called like this:

            https://example.org/on-select
                ?start=2016-02-04T2200:00.000Z
                &end=2016-02-05T2300:00.000Z
                &whole_day=no
                &view=month
    */
    selectUrl: null,

    /*
        The view shown initially
    */
    view: 'month',

    /*
        The date shown initially
    */
    date: null,

    /*
        The event ids to highlight for a short while
    */
    highlights: []
};

rc.events = [
    'rc-allocations-changed',
    'rc-reservation-error',
    'rc-reservations-changed'
];

rc.getFullcalendarOptions = function(options) {
    var rcOptions = $.extend(true, defaultOptions, options);

    // the fullcalendar default options
    var fcOptions = {
        allDaySlot: false,
        events: rcOptions.feed,
        minTime: rcOptions.minTime,
        maxTime: rcOptions.maxTime,
        editable: rcOptions.editable,
        selectable: rcOptions.editable,
        defaultView: rcOptions.view,
        highlights: rcOptions.highlights,
        afterSetup: [],
        viewRenderers: [],
        eventRenderers: [],
        reservations: rcOptions.reservations
    };

    // the reservation calendar type definition
    var views = [];

    switch (rcOptions.type) {
        case 'daypass':
            views = ['month'];
            fcOptions.header = {
                left: 'title today prev,next',
                center: '',
                right: ''
            };
            break;
        case 'room':
            views = ['month', 'agendaWeek', 'agendaDay'];
            fcOptions.header = {
                left: 'title today prev,next',
                center: '',
                right: views.join(',')
            };
            break;
        default:
            throw new Error("Unknown reservation calendar type: " + options.type);
    }

    // select a valid default view
    if (!_.contains(views, rcOptions.view)) {
        fcOptions.defaultView = views[0];
    }

    // implements editing
    if (rcOptions.editable) {

        // create events on selection
        fcOptions.select = function(start, end, _jsevent, view) {
            var url = new Url(rcOptions.selectUrl);
            url.query.start = start.toISOString();

            if (view.name === "month") {
                url.query.end = end.subtract(1, 'days').toISOString();
                url.query.whole_day = 'yes';
                url.query.view = view.name;
            } else {
                url.query.end = end.toISOString();
                url.query.whole_day = 'no';
                url.query.view = view.name;
            }
            window.location.href = url.toString();
        };

        // edit events on drag&drop, resize
        fcOptions.eventDrop = fcOptions.eventResize = function(event, _delta, _revertFunc, _jsEvent, _ui, view) {
            var url = new Url(event.editurl);
            url.query.start = event.start.toISOString();
            url.query.end = event.end.toISOString();
            url.query.view = view.name;
            location.href = url.toString();
        };

        // make sure other code can react if events are being changed
        fcOptions.eventDragStart = fcOptions.eventResizeStart = function(event) {
            event.is_changing = true;
        };
    }

    // after event rendering
    fcOptions.eventRenderers.push(rc.renderPartitions);
    fcOptions.eventRenderers.push(rc.highlightEvents);
    fcOptions.eventRenderers.push(rc.setupEventPopups);

    fcOptions.eventAfterRender = function(event, element, view) {
        var renderers = view.calendar.options.eventRenderers;
        for (var i = 0; i < renderers.length; i++) {
            renderers[i](event, element, view);
        }
    };

    // view change rendering
    fcOptions.viewRender = function(view, element) {
        var renderers = view.calendar.options.viewRenderers;
        for (var i = 0; i < renderers.length; i++) {
            renderers[i](view, element);
        }
    };

    // history handling
    rc.setupHistory(fcOptions);

    // reservation selection
    rc.setupReservationSelect(fcOptions);

    // setup allocation refresh handling
    fcOptions.afterSetup.push(rc.setupAllocationsRefetch);

    // switch to the correct date after the instance has been creted
    if (rcOptions.date) {
        fcOptions.afterSetup.push(function(calendar) {
            calendar.fullCalendar('gotoDate', rcOptions.date);
        });
    }

    return fcOptions;
};

$.fn.reservationCalendar = function(options) {
    var fcOptions = rc.getFullcalendarOptions($.extend(true, defaultOptions, options));

    return this.map(function(_ix, element) {

        var calendar = $(element).fullCalendar(fcOptions);

        for (var i = 0; i < fcOptions.afterSetup.length; i++) {
            fcOptions.afterSetup[i](calendar);
        }

        return calendar;
    });
};

// handles clicks on events
rc.setupEventPopups = function(event, element, view) {
    $(element).click(function() {
        var calendar = $(view.el.closest('.fc'));
        rc.showActionsPopup(calendar, element, event);
    });
};

// highlight events implementation
rc.highlightEvents = function(event, element, view) {
    if (_.contains(view.calendar.options.highlights, event.id)) {
        $(element).addClass('highlight');
    }
};

rc.setupAllocationsRefetch = function(calendar) {
    $(window).on('rc-allocations-changed', function() {
        calendar.fullCalendar('refetchEvents');
    });
};

// popup handler implementation
rc.showActionsPopup = function(calendar, element, event) {
    var wrapper = $('<div class="reservation-actions">');
    var reservation = $('<div class="reservation-form">').appendTo(wrapper);

    if (event.actions.length > 0) {
        $('<h3 />').text(locale('Allocation')).appendTo(wrapper);
        $(event.actions.join('')).appendTo(wrapper);
    }

    ReservationForm.render(reservation.get(0), event);

    rc.showPopup(calendar, element, wrapper);
};

rc.showErrorPopup = function(calendar, element, message) {
    rc.showPopup(calendar, element, message, 'top', ['error']);
};

rc.showPopup = function(calendar, element, content, position, extraClasses) {

    var options = {
        autoopen: true,
        tooltipanchor: element,
        type: 'tooltip',
        onopen: function() {
            rc.onPopupOpen.call(this, calendar);
        },
        onclose: function() {
            $(element).removeClass('has-popup');
        }
    };

    switch (position || 'right') {
        case 'top':
            options.horizontal = 'center';
            options.vertical = 'top';
            options.extraClasses = _.union(['top'], extraClasses || []);
            options.offsettop = -5;
            options.offsetleft = 20; // for some reason the popup's a bit off center
            break;
        case 'right':
            options.horizontal = 'right';
            options.vertical = 'middle';
            options.extraClasses = _.union(['right'], extraClasses || []);
            options.offsetleft = -10;
            break;
        default:
            throw Error("Unknown position: " + position);
    }

    $('<div class="popup" />').append(content).popup(options);
};

rc.onPopupOpen = function(calendar) {
    var popup = $(this);
    var options = popup.data('popupoptions');

    _.each(options.extraClasses, function(className) {
        popup.addClass(className);
    });

    var links = popup.find('a');

    // hookup all links with intercool
    links.each(function(_ix, link) {
        Intercooler.processNodes($(link));
    });

    // close the popup after any click on a link
    _.each(['ic.success', 'click'], function(eventName) {
        $(links).on(eventName, _.debounce(function() {
            popup.popup('hide');
        }));
    });

    // hookup the confirmation dialog
    var confirm_links = popup.find('a.confirm');
    confirm_links.confirmation();

    // pass all reservationcalendar events to the window
    _.each(rc.events, function(eventName) {
        links.on(eventName, _.debounce(function(_e, data) {
            $(calendar).trigger(eventName, [data, calendar, options.tooltipanchor]);
        }));
    });
};

// setup browser history handling
rc.setupHistory = function(fcOptions) {
    var isPopping = false;
    var isFirst = true;

    fcOptions.viewRenderers.push(function(view) {
        if (isPopping) {
            return;
        }

        var url = new Url(window.location.href);
        url.query.view = view.name;
        url.query.date = view.intervalStart.format('YYYYMMDD');

        var state = [
            {
                'view': view.name,
                'date': view.intervalStart
            },
            document.title + ' ' + view.title,
            url.toString()
        ];

        if (isFirst) {
            window.history.replaceState.apply(window.history, state);
            isFirst = false;
        } else {
            window.history.pushState.apply(window.history, state);
        }
    });

    fcOptions.afterSetup.push(function(calendar) {
        window.onpopstate = function(event) {
            if (event.state === null) {
                return;
            }

            isPopping = true;
            calendar.fullCalendar('changeView', event.state.view);
            calendar.fullCalendar('gotoDate', event.state.date);
            isPopping = false;
        };
    });
};

// setup the reservation selection on the left
rc.setupReservationSelect = function(fcOptions) {
    var selection = null;

    fcOptions.afterSetup.push(function(calendar) {
        var view = $(calendar).find('.fc-view-container');

        selection = $('<div class="reservation-selection"></div>')
            .insertBefore(view);

        calendar.fullCalendar('option', 'aspectRatio', 1.1415926);

        calendar.on('rc-reservation-error', function(_e, data, _calendar, target) {
            rc.showErrorPopup(calendar, target || calendar.find('.fc-view'), data.message);
        });

        calendar.on('rc-reservations-changed', function() {
            $.getJSON(fcOptions.reservations, function(reservations) {
                ReservationSelection.render(selection.get(0), calendar, reservations);
            });
        });

        ReservationSelection.resize(selection);
        calendar.trigger('rc-reservations-changed');
    });

    var resize = function() {
        ReservationSelection.resize(selection);
    };

    fcOptions.windowResize = resize;
    fcOptions.viewRenderers.push(resize);
};

// renders the occupied partitions on an event
rc.renderPartitions = function(event, element, calendar) {

    if (event.is_moving) {
        return;
    }

    var free = _.template('<div style="height:<%= height %>%;"></div>');
    var used = _.template('<div style="height:<%= height %>%;" class="calendar-occupied"></div>');
    var partition_block = _.template('<div style="height:<%= height %>px;"><%= partitions %></div>');

    // build the individual partitions
    var event_partitions = rc.adjustPartitions(
        event,
        moment.duration(calendar.options.minTime).hours(),
        moment.duration(calendar.options.maxTime).hours()
    );

    var partitions = '';
    _.each(event_partitions, function(partition) {
        var reserved = partition[1];
        if (reserved === false) {
            partitions += free({height: partition[0]});
        } else {
            partitions += used({height: partition[0]});
        }
    });

    // locks the height during resizing
    var height = element.outerHeight(true);
    if (event.is_changing) {
        height = event.height;
        $(element).addClass('changing');
    } else {
        event.height = height;
    }

    // render the whole block
    var html = partition_block({height: height, partitions: partitions});
    $('.fc-bg', element).wrapInner(html);
};

// partitions are relative to the event. Since depending on the
// calendar only part of an event may be shown, we need to account
// for that fact. This function takes the event, and the range of
// the calendar and adjusts the partitions if necessary.
rc.adjustPartitions = function(event, min_hour, max_hour) {

    if (_.isUndefined(event.partitions)) {
        return event.partitions;
    }

    // clone the partitions
    var partitions = _.map(event.partitions, _.clone);
    var start_hour = event.start.hours();
    var end_hour = event.end.hours() === 0 ? 24 : event.end.hours();
    var duration = end_hour - start_hour;

    // if the event fits inside the calendar hours, all is ok
    if (min_hour <= start_hour && end_hour <= max_hour) {
        return partitions;
    }

    // if the whole event contains only one partition, no move will
    // change anything
    if (partitions.length <= 1) {
        return partitions;
    }

    // the event is rendered within the calendar, with the top and
    // bottom cut off. The partitions are calculated assuming the
    // event is being rendered as a whole. To adjust we cut the
    // bottom and top from the partitions and blow up the whole event.
    //
    // It made sense when I wrote the initial implementation :)
    var percentage_per_hour = 1 / duration * 100;
    var top_margin = 0, bottom_margin = 0;

    if (start_hour < min_hour) {
        top_margin = (min_hour - start_hour) * percentage_per_hour;
    }
    if (end_hour > max_hour) {
        bottom_margin = (end_hour - max_hour) * percentage_per_hour;
    }

    partitions = rc.removeMarginFromPartitions(partitions, top_margin);
    partitions.reverse();

    partitions = rc.removeMarginFromPartitions(partitions, bottom_margin);
    partitions.reverse();

    // blow up the result to 100%;
    var total = rc.sumPartitions(partitions);
    _.each(partitions, function(partition) {
        partition[0] = partition[0] / total * 100;
    });

    return partitions;
};

// remove the given margin from the top of the partitions array
// the margin is given as a percentage
rc.removeMarginFromPartitions = function(partitions, margin) {

    if (margin === 0) {
        return partitions;
    }

    var removed_total = 0;
    var original_margin = margin;

    for (var i = 0; i < partitions.length; i++) {
        if (rc.roundNumber(partitions[i][0]) >= rc.roundNumber(margin)) {
            partitions[i][0] = partitions[i][0] - margin;
            break;
        } else {
            removed_total += partitions[i][0];
            margin -= partitions[i][0];
            partitions.splice(i, 1);

            i -= 1;

            if (removed_total >= original_margin) {
                break;
            }
        }
    }

    return partitions;
};

rc.roundNumber = function(num) {
    return +Number(Math.round(num + "e+2") + "e-2");
};

rc.sumPartitions = function(partitions) {
    return _.reduce(partitions, function(running_total, p) {
        return running_total + p[0];
    }, 0);
};

/*
    Shows the list of reservations to be confirmed.
*/
ReservationSelection = React.createClass({
    handleClick: function(reservation) {
        var calendar = $(this.props.calendar);

        $.ajax({
            url: reservation.delete,
            type: 'DELETE',
            success: function() {
                calendar.trigger('rc-reservations-changed');
            }
        });
    },
    render: function() {
        var self = this;
        return (
            <div className="reservation-selection-inner">
                <h3>{locale("Dates")}</h3>
                {
                    this.props.reservations.length === 0 &&
                        <p>{locale("Select allocations on the left to reserve them")}</p>
                }
                {
                    this.props.reservations.length > 0 &&
                        <ul>{
                            _.map(this.props.reservations, function(r, ix) {
                                var boundClick = self.handleClick.bind(self, r);
                                return (
                                    <li key={ix} className={r.className + " reservation"}>
                                        <span className="reservation-date">{r.date}</span>
                                        <span className="reservation-time">{r.time}</span>
                                        <a className="delete" onClick={boundClick}>{locale('Remove')}</a>
                                    </li>
                                );
                            })
                        }</ul>
                }
                <a href="#" className={this.props.reservations.length === 0 && 'disabled button secondary' || 'button'}>
                    {locale("Reserve")}
                </a>
            </div>
        );
    }
});

ReservationSelection.render = function(element, calendar, reservations) {
    React.render(<ReservationSelection calendar={calendar} reservations={reservations} />, element);
};

ReservationSelection.resize = function(selection) {
    var element = $(selection);
    var view = element.parent().find('.fc-view-container');

    element.css('min-height', view.height());
};

/*
    Allows to fine-adjust the reservation before adding it.
*/
ReservationForm = React.createClass({
    getInitialState: function() {
        return {
            start: !this.props.wholeDay && this.props.start.format('HH:mm') || "",
            end: !this.props.wholeDay && this.props.end.format('HH:mm') || "",
            quota: 1,
            wholeDay: this.props.wholeDay
        };
    },
    handleChangeWholeDay: function(e) {
        var state = _.extend({}, this.state.selected);
        state.wholeDay = e.target.value === 'yes';
        this.setState(state);
    },
    render: function() {
        return (
            <form>
                {this.props.partlyAvailable && this.props.wholeDay && (
                    <div className="field">
                        <span className="label-text">{locale("Whole day")}</span>

                        <input id="reserve-whole-day-yes"
                            name="reserve-whole-day"
                            type="radio"
                            value="yes"
                            checked={this.state.wholeDay}
                            onChange={this.handleChangeWholeDay}
                        />
                        <label htmlFor="reserve-whole-day-yes">{locale("Yes")}</label>
                        <input id="reserve-whole-day-no"
                            name="reserve-whole-day"
                            type="radio"
                            value="no"
                            checked={!this.state.wholeDay}
                            onChange={this.handleChangeWholeDay}
                        />
                        <label htmlFor="reserve-whole-day-no">{locale("No")}</label>
                    </div>
                )}

                {this.props.partlyAvailable && (!this.props.wholeDay || !this.state.wholeDay) && (
                    <div className="field split">
                        <div>
                            <label htmlFor="start">{locale("From")}</label>
                            <input name="start" type="time" size="4" defaultValue={this.state.start}/>
                        </div>
                        <div>
                            <label htmlFor="end">{locale("Until")}</label>
                            <input name="end" type="time" size="4" defaultValue={this.state.end}/>
                        </div>
                    </div>
                )}
                {!this.props.partlyAvailable && this.props.quota > 1 && (
                    <div className="field">
                        <div>
                            <label htmlFor="count">{locale("Count")}</label>
                            <input name="count" type="number" size="4" defaultValue={this.state.quota}/>
                        </div>
                    </div>
                )}

                <button className="button">{locale("Add")}</button>
            </form>
        );
    }
});

ReservationForm.render = function(element, event) {
    React.render(
        <ReservationForm
            partlyAvailable={event.partlyAvailable}
            quota={event.quota}
            quotaLeft={event.quotaLeft}
            start={event.start}
            end={event.end}
            wholeDay={event.wholeDay}
        />,
    element);
};
