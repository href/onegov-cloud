var FormcodeSelect = React.createClass({
    getInitialState: function() {
        var values = this.getTarget().value.split('\n').filter(function(line) {
            return line.trim() !== '';
        });

        var selected = {};
        values.forEach(function(value) {
            selected[value] = true;
        });

        return {
            fields: [],
            missing: {},
            selected: selected
        };
    },
    getSelectionAsText: function(selected) {
        var fields = Object.getOwnPropertyNames(selected || this.state.selected);

        var order = this.state.fields.map(function(field) {
            return field.human_id;
        });

        fields.sort(function(a, b) {
            return order.indexOf(a) - order.indexOf(b);
        });

        return fields.join('\n');
    },
    getTarget: function() {
        var target = this.props.target;
        return target instanceof Element && target || document.querySelector(target);
    },
    cloneState: function() {
        return JSON.parse(JSON.stringify(this.state));
    },
    isKnownField: function(fields, attribute, value) {
        for (var i = 0; i < fields.length; i++) {
            if (fields[i][attribute] === value) {
                return true;
            }
        }
        return false;
    },
    onUpdateFields: function(fields) {
        var self = this;

        var state = this.cloneState();
        state.fields = fields;

        // fields which are selected but missing are kept around to select them
        // again later if the field reappears - if it doesn't, the selection
        // isn't submitted to the backend
        Object.keys(state.selected).forEach(function(field) {
            if (!self.isKnownField(fields, 'human_id', field)) {
                state.missing[field] = true;
                delete state.selected[field];
            }
        });

        // fields which reappear are selected again
        fields.forEach(function(field) {
            if (state.missing[field.human_id] === true) {
                state.selected[field.human_id] = true;
                delete state.missing[field.human_id];
            }
        });

        this.setState(state);
        this.getTarget().value = this.getSelectionAsText(state.seleted);
    },
    onSelect: function(human_id) {
        var state = this.cloneState();

        if (this.props.type === 'radio') {
            state.selected = {};
        }

        if (typeof state.selected[human_id] === 'undefined') {
            state.selected[human_id] = true;
        } else {
            delete state.selected[human_id];
        }

        this.setState(state);
        this.getTarget().value = this.getSelectionAsText(state.selected);
    },
    isSelected: function(field) {
        return field.human_id in this.state.selected;
    },
    render: function() {
        var self = this;
        return (
            <WatchedFields
                include={this.props.include}
                exclude={this.props.exclude}
                watcher={this.props.watcher}
                handler={this.onUpdateFields}
            >
                <div className="formcode-select">
                    {
                        self.state.fields && self.state.fields.map(function(field) {
                            return (
                                <FormcodeSelectField
                                    key={field.id}
                                    id={field.human_id}
                                    selected={self.isSelected(field)}
                                    label={field.human_id}
                                    handler={self.onSelect}
                                    type={self.props.type}
                                />
                            );
                        })
                    }
                </div>
            </WatchedFields>
        );
    }
});

var FormcodeSelectField = React.createClass({
    handleChange: function() {
        this.props.handler(this.props.id);
    },
    render: function() {
        return (
            <label>
                <input
                    type={this.props.type}
                    checked={this.props.selected}
                    onChange={this.handleChange}
                />
                {this.props.label}
            </label>
        );
    }
});

var initFormcodeSelect = function(container, watcher, target, type, include, exclude) {
    var el = container.appendChild(document.createElement('div'));
    ReactDOM.render(
        <FormcodeSelect
            watcher={watcher}
            type={type}
            target={target}
            include={include}
            exclude={exclude}
        />,
        el
    );
};
