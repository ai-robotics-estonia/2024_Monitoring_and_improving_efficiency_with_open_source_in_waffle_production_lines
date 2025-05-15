# Balsnack / AIRE / TalTech data integration solution

The following repository contains the code for Balsnack data collection solution. 

The overall solution consists of the following components:
- EMQ Neuron - data adapter that allows to transform industrial communication protocols (in this case OPC-UA) to MQTT.
- EMQX - MQTT broker that allows to publish and subscribe to messages.
- MQTTX - MQTT client that allows to check data manually
- Home Assistant - home automation platform that acts as a simple SCADA system. It allows to visualize the data and control the devices.

The repository contains the following resources:
- `/services` - source codes of configuration files needed for solution
    - `/services/emq-neuron` - EMQ Neuron + EMQX configuration files
- `/docs` - documentation of the solution
- `/dev` - development resources for the solution
    - `/dev/opc-ua-simulator` - OPC-UA simulator that allows to verify the solution locally to test the data collection and visualization, without actual industrial machinery


