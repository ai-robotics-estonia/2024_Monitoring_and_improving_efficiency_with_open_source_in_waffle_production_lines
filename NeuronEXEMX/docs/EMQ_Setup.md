# Finding OPC UA Tags with EMQ Neuron

This guide explains how to discover and configure OPC UA tags using EMQ Neuron and the free OPC UA client. The integration lets you easily connect industrial OPC UA devices with MQTT-based IoT platforms.

## Prerequisites

- Docker and Docker Compose installed
- Basic understanding of OPC UA protocol
- An OPC UA server to connect to

## 1. Setting Up the Environment

The following Docker Compose file sets up the required environment:

```yaml
version: "3.8"

services:
  neuron:
    image: emqx/neuron:2.5.3-alpine
    container_name: neuron
    restart: always
    privileged: true
    ports:
      - "7000:7000"
    volumes:
      - /host/dir:/opt/neuron/persistence
    environment:
      - TZ=Europe/Tallinn
      - EMQX_LOG__LEVEL=debug
      - DISABLE_AUTH=1
    depends_on:
      - emqx

  emqx:
    image: emqx:latest
    container_name: emqx
    restart: always
    ports:
      - "18083:18083"
      - "1883:1883"
    environment:
      - TZ=Europe/Tallinn
      - EMQX_LOG__LEVEL=debug
      - EMQX_AUTH__ANONYMOUS__ENABLED=true
      - EMQX_AUTH__ANONYMOUS__USERNAME=emqx_user
      - EMQX_AUTH__ANONYMOUS__PASSWORD=public_password
```

Launch the containers:

```bash
docker-compose up -d
```

## 2. Accessing the Neuron Dashboard

Open your browser and navigate to:

```
http://localhost:7000
```

You'll see the Neuron dashboard with two main navigation sections:
- Monitoring
- Configuration

![Neuron Dashboard](/docs/images/image1.png)

## 3. Configuring South Devices (OPC UA Server)

South Devices refers to the data sources (industrial devices/PLCs) from which Neuron collects data.

### 3.1 Adding an OPC UA Device

1. Navigate to Configuration → South Devices
2. Click the "+ Add Device" button
3. Enter device details:
   - Name: Give your device a name (e.g., "festo-fms")
   - Select plugin type: "OPC UA"

![South Devices](./images/Neuron%20-%20Devices.png)

### 3.2 Configuring Device Connection

1. After adding the device, you'll be taken to the device configuration page
2. Enter the OPC UA server endpoint URL (e.g., "opc.tcp://192.168.0.166:4840")
3. If required, enter authentication details (username/password)
4. Upload certificate and key files if using secure connection
5. Click "Submit"

![Device Configuration](./images/Neuron%20-%20Devices.png)

## 4. Finding OPC UA Tags Using FreeOpcUa Client

Before configuring tags in Neuron, it's helpful to explore the OPC UA server structure to identify the tags you want to monitor.

### 4.1 Installing and Running FreeOpcUa Client

1. Download and install FreeOpcUa Client from [https://github.com/FreeOpcUa/opcua-client-gui](https://github.com/FreeOpcUa/opcua-client-gui)
2. Launch the application
3. Enter the OPC UA server endpoint URL (same as used in Neuron)
4. Click "Connect"

### 4.2 Browsing OPC UA Nodes

1. Once connected, you'll see the node tree structure on the left side
2. Expand the nodes to explore the available tags
3. In our example, we can see nodes for:
   - IsRunning (Boolean)
   - Pressure
   - Temperature

![FreeOpcUa Client](./images/OpcUaClient%20-%20Namespace%20View.png)

### 4.3 Finding Node Identifiers

1. Select a node in the tree (e.g., "IsRunning")
2. View the node attributes on the right panel
3. Note down the NodeId (e.g., "ns=1;i=1001") - you'll need this when configuring tags in Neuron

![Node Attributes](./images/OpcUaClient%20-%20Tag%20ID.png)

## 5. Creating Tag Groups in Neuron

Tag groups allow you to organize related tags and set common polling intervals.

### 5.1 Adding a Tag Group

1. In Neuron, navigate to your device's Group List page
2. Click the "Create" button
3. Enter a group name (e.g., "Points")
4. Set the polling interval (e.g., 100ms)
5. Click "Submit"

![Group List](/docs/images/image4.png)
![Edit Group](/docs/images/image5.png)

## 6. Adding OPC UA Tags to Neuron

Now that you've identified the tags you want to monitor, add them to Neuron.

### 6.1 Navigating to Tag List

1. Go to the Tag List page for your device
2. Click the "Create" button


![Tag List](./images/Neuron%20-%20Groups.png)
![Tag List](./images/Neuron%20-%20Group%20Setup.png)

### 6.2 Adding Tags

For each tag you want to monitor:

1. Enter the tag details:
   - Name: A descriptive name for the tag (e.g., "Status", "Temperature")
   - Address: The NodeId from FreeOpcUa Client (e.g., 111001 for Status)
   - Type: The data type (e.g., BOOL, DOUBLE)
   - Attribute: Select Read/Subscribe for monitoring
2. Click "Submit"

![Edit Tag](/docs/images/image7.png)

### 6.3 Verifying Tag Data

1. Navigate to Data Monitoring
2. You should see your device and group
3. The current values of your tags will be displayed with their updated values

![Data Monitoring](./images/Neuron%20-%20Tags%20when%20connected.png)

## 7. Configuring North Apps (MQTT Connection)

North Apps connect Neuron to external systems like MQTT brokers.

### 7.1 Viewing North Apps

1. Navigate to Configuration → North Apps
2. You should see the EMQX application that was created automatically

![North Apps](./images/Neuron%20-%20Apps.png)

### 7.2 Configuring MQTT Connection

1. Click on the EMQX application to configure it
2. Configure the settings:
   - Client ID: A unique identifier
   - QoS Level: Quality of Service level (0, 1, or 2)
   - Upload Format: Choose between Values-format or Tags-format
   - Write Request/Response Topics: Topics for sending requests and receiving responses
   - Broker Host: MQTT broker hostname/IP (e.g., "emqx")
   - Broker Port: MQTT broker port (typically 1883)
   - Authentication (if required): Username and password
   - SSL: Enable/disable secure connection
3. Click "Submit"

![MQTT Configuration Part 1](./images/Neuron%20-%20EMQX%20Setup.png)
![MQTT Configuration Part 2](./images/Neuron%20-%20EMQX%20Setup.png)

## 8. Testing Data Flow

1. Check the dashboard for the EMQX application

![MQTT Dashboard](./images/EMQX%20-%20Overview.png)

If everything is set up correctly, you should see number of messages sent and received. 

## 9. Viewing raw data in MQTTX

1. Open MQTTX and connect to your MQTT broker

![MQTTX](./images/MQTTX%20-%20Connection%20Setup.png)

2. Subscribe to all topics to see the data being sent from Neuron (write `#` in the topic field)

![MQTTX](./images/MQTTX%20-%20Subscription%20Setup.png)

3. If everything is set up correctly, you should see the data being sent from Neuron to the MQTT broker

![MQTTX](./images/MQTTX%20-%20Messages.png)

4. You can see a topic tree with the data being sent. The topic structure is as follows:

![MQTTX](./images/MQTTX%20-%20Topic%20View.png

## 10. Troubleshooting

If tags aren't updating or showing incorrect values:

1. Check device connection status in South Devices
2. Verify OPC UA server endpoint URL and credentials
3. Ensure node addresses are correct
4. Check polling interval settings
5. Verify MQTT broker connection in North Apps

## Conclusion

You've successfully configured EMQ Neuron to discover and monitor OPC UA tags and send the data to an MQTT broker. This setup creates a bridge between industrial OPC UA devices and modern IoT platforms, enabling real-time data monitoring and analytics.