import React from 'react';
import ReactDOM from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css'
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';

import {LineChart, XAxis, YAxis, Line, Tooltip, CartesianGrid} from 'recharts';
import App from './App.js';


class Main extends React.Component {
    
    renderGraphs(data) {
        const graphable = data.map((element, tick) => {
            return({
                tick: tick,
                value: element,
            });
        })
        return(
            <div className="graphBody"><LineChart width={600} height={500} data={graphable}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="tick" />
            <YAxis />
             <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#8884d8" />
        </LineChart></div>
            
        );
    }

    render() {
        const graphData = [300, 200, 500, 300, 100, 50, 600, 120];
        return (
            <Container id="mainContainer" fluid>
                <Row>
                    <Col className="column">
                        {this.renderGraphs(graphData)}
                    </Col>
                    <Col>
                        <App />
                    </Col>
                    
                </Row>
            </Container>
        );
    }
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<Main />);


