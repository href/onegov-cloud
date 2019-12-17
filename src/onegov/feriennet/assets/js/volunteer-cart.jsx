var VolunteerCart = React.createClass({
    getInitialState: function() {
        return {'items': []};
    },
    refresh: function() {
        var self = this;

        $.getJSON(this.props.cartURL, function(data) {
            self.setState({'items': data});
        });
    },
    remove: function(item) {
        var self = this;

        $.post(item.remove, function() {
            self.refresh();
        });
    },
    render: function() {
        var self = this;

        var boundRemove = function(item) {
            return function() {
                self.remove(item);
            };
        };

        return (
            <div className="volunteer-cart">
                <div>{
                    self.state.items && self.state.items.map(function(item) {
                        return (
                            <div key={item.need_id} className="volunteer-cart-item">
                                <div className="cart-item-activity">
                                    {item.activity}
                                </div>
                                <div className="cart-item-dates">
                                    <ul className="dense">{
                                        item.dates.map(function(date) {
                                            return (<li key={date}>{date}</li>);
                                        })
                                    }</ul>
                                </div>
                                <div className="cart-item-remove">
                                    <a onClick={boundRemove(item)}>{self.props.removeLabel}</a>
                                </div>
                                <div className="cart-item-need">
                                    {item.need}
                                </div>
                            </div>
                        );
                    })
                }</div>
                <div>{
                    self.state.items && <a className="button">
                        {self.props.buttonLabel}
                    </a>
                }</div>
            </div>
        );
    }
});

jQuery.fn.volunteerCart = function() {
    var container = $(this);
    var el = container.get(0).appendChild(document.createElement('div'));

    var cart = ReactDOM.render(
        <VolunteerCart
            emptyLabel={container.attr('data-empty-label')}
            buttonLabel={container.attr('data-button-label')}
            removeLabel={container.attr('data-remove-label')}
            cartURL={container.attr('data-cart-url')}
        />, el
    );

    cart.refresh();

    window.volunteerCarts = window.volunteerCarts || [];
    window.volunteerCarts.push(cart);
};

$(document).ready(function() {
    $('.volunteer-cart-widget').volunteerCart();

    window.refreshVolunteerCarts = function() {
        window.volunteerCarts.forEach(function(cart) {
            cart.refresh();
        });
    };
});
