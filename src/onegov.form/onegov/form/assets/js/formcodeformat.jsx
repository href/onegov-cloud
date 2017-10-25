var FormCodeFormat = React.createClass({
    getInitialState: function() {
        return {fields: []};
    },
    componentDidMount: function() {
        this.unsubscribe = this.props.watcher.subscribe(this.update);
    },
    componentWillUnmount: function() {
        this.unsubscribe();
    },
    update: function(fields) {
        var filtered = [];

        if (fields.forEach !== undefined) {
            fields.forEach(function(field) {
                if (!(/(fileinput|radio|checkbox)/).test(field.type)) {
                    filtered.push(field);
                }
            });
        }

        this.setState({fields: filtered});
    },
    render: function() {
        return (
            this.state.fields.length > 0 && (
                <div className="formcode-toolbar">
                    <ToggleButton icon="fa-plus-circle">
                        <FormCodeFormatFields
                            fields={this.state.fields}
                            target={this.props.target}
                        />
                    </ToggleButton>
                </div>
            )
        );
    }
});

var FormCodeFormatFields = React.createClass({
    render: function() {
        var self = this;
        return (
            <div className="formcode-snippets">
                {
                    self.props.fields.map(function(field, ix) {
                        return (
                            <FormCodeFormatField
                                key={ix}
                                field={field}
                                target={self.props.target}
                            />
                        );
                    })
                }
            </div>
        );
    }
});

var FormCodeFormatField = React.createClass({
    handleClick: function() {
        var format = '[' + this.props.field.human_id + ']';
        formcodeUtils.updateTarget(this.props.target, format, null, ' ');
    },
    render: function() {
        return (
            <div className="formcode-snippet" onClick={this.handleClick}>
                <div className="formcode-snippet-name">
                    {this.props.field.human_id}
                </div>
            </div>
        );
    }
});

// attaches itself to the given formcode format watcher and keeps a list
// of available fields in a list to be inserted as safe formats
var initFormcodeFormat = function(container, watcher, target) {
    watcher = watcher || formcodeWatcherRegistry.get(container.getAttribute('data-watcher'));
    target = target || container.getAttribute('data-target');

    if (watcher === undefined || target === undefined) {
        return;
    }

    var el = container.appendChild(document.createElement('div'));
    ReactDOM.render(
        <FormCodeFormat watcher={watcher} target={target} />,
        el
    );
};

// automatically hooks up all formcode snippet elements
document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll('.formcode-format').forEach(initFormcodeFormat);
});
