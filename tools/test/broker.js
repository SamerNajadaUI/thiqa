const aedes = require('aedes')();
const { createServer } = require('aedes-server-factory');
createServer(aedes, { ws: true }).listen(8883, () => console.log('ws broker 8883'));
