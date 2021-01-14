import React, { Fragment } from "react";
import './App.css';

const WEB_SERVICE_ENDPOINT = "https://blooming-mesa-32203.herokuapp.com"

const PACKAGE_STATUS = {
    WAITING: "waiting",
    ON_THE_WAY: "on the way",
    RECEIVED: "received"
}

function UndoButton(props) {

    var isDisabled = true;

    if (props.status === PACKAGE_STATUS.WAITING) {
        isDisabled = true;
    } else {
        isDisabled = false;
    }

    var onUndoButtonClick = () => {
        switch (props.status) {
        case PACKAGE_STATUS.ON_THE_WAY:
            props.changePackageStatus(props.packageId, PACKAGE_STATUS.WAITING);
            break;
        case PACKAGE_STATUS.RECEIVED:
            props.changePackageStatus(props.packageId, PACKAGE_STATUS.ON_THE_WAY);
            break;
        }
    }

    return <button className="status-button" type="button" disabled={isDisabled} onClick={onUndoButtonClick}>Undo</button>;
}

function StatusButton(props) {


	var onTakeButtonClick = () => {
        props.changePackageStatus(props.packageId, PACKAGE_STATUS.ON_THE_WAY);
    }

    var onReceiveButtonClick = () => {
        props.changePackageStatus(props.packageId, PACKAGE_STATUS.RECEIVED);
    }

    if (props.status === PACKAGE_STATUS.WAITING) {
        return <button className="status-button" type="button" onClick={onTakeButtonClick}>Odebrano</button>;
    } else if (props.status === PACKAGE_STATUS.ON_THE_WAY) {
        return <button className="status-button" type="button" onClick={onReceiveButtonClick}>Dostarczono</button>;
    } else {
        return <Fragment>Zrobione!</Fragment>;
    }
}

function PackagesList(props) {

    var packageStatusNameMapper = (status) => {
        switch (status) {
        case PACKAGE_STATUS.WAITING:
                return "Oczekujace";
        case PACKAGE_STATUS.ON_THE_WAY:
                return "W drodze";
        case PACKAGE_STATUS.RECEIVED:
            return "Dostarczono";
        } 
    }

    if(props.isLoaded) {
        return (
            <table>
                <thead>
                <tr>
                    <th>Identyfikator</th>
                    <th>Adres odbiorcy</th>
                    <th>Identyfikator skrytki</th>
                    <th>Romiar paczki</th>
                    <th>Status paczki</th>
                </tr>
                </thead>
                <tbody>
                {props.packages.map((p) => {
                        return (
                            <tr key={p.packageId}>
                                <th>{p.packageId}</th>
                                <th>{p.receiver}</th>
                                <th>{p.postId}</th>
                                <th>{p.size}</th>
                                <th>{packageStatusNameMapper(p.status)}</th>
                                <th><StatusButton status={p.status} packageId={p.packageId} changePackageStatus={props
                                    .changePackageStatus}/></th>
                                <th><UndoButton status={p.status} packageId={p.packageId} changePackageStatus={props
                                    .changePackageStatus}/></th>
                            </tr>
                        );
                    }
                )}
                </tbody>
            </table>
        );
    }

    return(
        <div>
            <h1>{props.info}</h1>
        </div>
    );
}

class App extends React.Component {
	constructor(props) {
        super(props);
		this.state = {
			packages: [],
            isLoaded: false,
            info: "Za chwile pojawia sie paczki..."
		}
	}

    changePackageStatus(id, status) {

        var url;
        const newPackages = this.state.packages.map((p) => {
            if (p.packageId === id) {
                p.status = status;
                url = p["_links"]["update"]["href"];
            }

            return p;
        });

        this.setState({
            packages: newPackages
        });

        var endpoint = WEB_SERVICE_ENDPOINT + url;

        const requestOptions = {
            method: 'PUT',
            headers: { "Authorization": "Bearer " + "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2dpbiI6ImNvdXJpZXIifQ.nuQGdT09dzWtswTZ26Gtt9LwOBpdRD_VGXzoY2kHafo", "Content-Type": "application/json" },
            body: JSON.stringify({ status: status })
        };

        fetch(endpoint, requestOptions);
    }
	
	componentDidMount() 
	{
        const requestOptions = {
        method: 'GET',
        headers: {"Authorization": "Bearer " + "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2dpbiI6ImNvdXJpZXIifQ.nuQGdT09dzWtswTZ26Gtt9LwOBpdRD_VGXzoY2kHafo"},
		};

        fetch(WEB_SERVICE_ENDPOINT + '/sender/dashboard', requestOptions)
            .then(response => {
                if (response.status !== 200) {
                    this.setState({ info: "Blad serwera" });
                }
                return response.json();
            })
            .then(data => {
                var dashboard = [];
                for (var p in data["_embedded"]) {
                    dashboard.push(data["_embedded"][p]);
                }
                this.setState({ packages: dashboard, isLoaded: true });
            });
    }
	
	
	render(){
		
		return (
            <div className="App">
                <PackagesList packages={this.state.packages} isLoaded={this.state.isLoaded} info={this.state.info} changePackageStatus={this.changePackageStatus.bind(this)} />
		</div>
	  );
	}
}

export default App;
