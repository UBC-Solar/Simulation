import React, { useState } from "react";

var client = require('websocket').client;
var W3CWebSocket = require('websocket').w3cwebsocket;


// messing around with making the messages appear in a list - Felix

// function PrintMessages(props) {
//   console.log("PRINTING")
//   const list = props.messages.map((mess, index)=>{
//     return(
//     <li key={index}>
//       {mess}
//     </li>);
//   })
//   console.log(list);
//   return list;
// }


function  App() {
  
  const [messageData, setMessages] = useState('');

  const ws = new W3CWebSocket('ws://127.0.0.1:8000/ws/server/');

  function sendDateRequest() {
    ws.send(JSON.stringify({'requestType': 'date'}));
  }

  ws.onopen = (event) => {
    console.log("connected");
  };

  ws.onmessage = function (event) {
    const json = JSON.parse(event.data);
    //setMessages(json.message);
    console.log(json.message.toString());
  };

  return (<button onClick={sendDateRequest}>Default</button>);
}

export default  App;