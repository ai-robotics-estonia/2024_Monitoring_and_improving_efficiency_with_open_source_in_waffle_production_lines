import {
    OPCUAServer,
    Variant,
    DataType,
    StatusCodes,
    VariantArrayType,
    UAObject,
    UAVariable,
    AttributeIds,
    AddressSpace,
    ServerEngine,
} from "node-opcua";
import path from "path";

// Configuration for the OPC UA server
const SERVER_CONFIG = {
    port: 4840,
    resourcePath: "/UA/MachineSim",
    buildInfo: {
        productName: "MachineSim",
        buildNumber: "1",
        buildDate: new Date(),
    },
};

// Define the interface for our machine simulator
interface MachineState {
    isRunning: boolean;
    temperature: number;
    pressure: number;
}

class MachineSimulator {
    private server: OPCUAServer;
    private addressSpace: AddressSpace | null = null;
    private namespace: number = 1;
    private simulationInterval: NodeJS.Timeout | null = null;
    private machineState: MachineState = {
        isRunning: false,
        temperature: 22.0,
        pressure: 1.0,
    };

    constructor() {
        this.server = new OPCUAServer({
            port: SERVER_CONFIG.port,
            resourcePath: SERVER_CONFIG.resourcePath,
            buildInfo: SERVER_CONFIG.buildInfo,
            // serverCertificateManager: {
            //     automaticallyAcceptUnknownCertificate: true,
            // },
        });
    }

    /**
     * Initialize the OPC UA server
     */
    async initialize(): Promise<void> {
        try {
            await this.server.initialize();
            console.log("OPC UA server initialized");

            // Set up the address space
            this.setupAddressSpace();

            // Start the simulation
            this.startSimulation();
        } catch (err) {
            console.error("Error initializing server:", err);
            throw err;
        }
    }

    /**
     * Set up the address space with our machine tags
     */
    private setupAddressSpace(): void {
        this.addressSpace = this.server.engine.addressSpace;

        if (!this.addressSpace) {
            throw new Error("AddressSpace is not initialized");
        }

        // Create a folder for our machine
        const namespace = this.addressSpace.getOwnNamespace();
        const machineFolder = namespace.addFolder("ObjectsFolder", {
            browseName: "Machine",
        });

        // Add variables for the machine state
        this.addMachineVariables(namespace, machineFolder);
    }

    /**
     * Add machine variables to the address space
     */
    private addMachineVariables(namespace: any, machineFolder: UAObject): void {
        // Boolean tag: isRunning
        const isRunningNode = namespace.addVariable({
            organizedBy: machineFolder,
            browseName: "IsRunning",
            dataType: "Boolean",
            value: {
                get: () => {
                    return new Variant({
                        dataType: DataType.Boolean,
                        value: this.machineState.isRunning,
                    });
                },
                set: (variant: Variant) => {
                    if (variant.dataType === DataType.Boolean) {
                        this.machineState.isRunning = variant.value as boolean;
                        return StatusCodes.Good;
                    }
                    return StatusCodes.BadTypeMismatch;
                },
            },
        });
        // isRunningNode.setFlag("Historizing", true);

        // Float tag: temperature
        const temperatureNode = namespace.addVariable({
            organizedBy: machineFolder,
            browseName: "Temperature",
            dataType: "Double",
            value: {
                get: () => {
                    return new Variant({
                        dataType: DataType.Double,
                        value: this.machineState.temperature,
                    });
                },
            },
        });
        // temperatureNode.setFlag("Historizing", true);

        // Float tag: pressure
        const pressureNode = namespace.addVariable({
            organizedBy: machineFolder,
            browseName: "Pressure",
            dataType: "Double",
            value: {
                get: () => {
                    return new Variant({
                        dataType: DataType.Double,
                        value: this.machineState.pressure,
                    });
                },
            },
        });
        // pressureNode.setFlag("Historizing", true);
    }

    /**
     * Start the simulation by updating tag values at intervals
     */
    private startSimulation(): void {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
        }

        this.simulationInterval = setInterval(() => {
            // Randomly toggle the running state (20% chance)
            if (Math.random() < 0.2) {
                this.machineState.isRunning = !this.machineState.isRunning;
            }

            // Update temperature with some random variation (if machine is running, it gets hotter)
            const tempDelta = (Math.random() - 0.5) * 2; // Random change between -1 and 1
            if (this.machineState.isRunning) {
                this.machineState.temperature = Math.min(
                    80.0,
                    this.machineState.temperature + tempDelta + 0.2
                );
            } else {
                // If not running, tend toward ambient temperature (22.0)
                this.machineState.temperature =
                    this.machineState.temperature + (22.0 - this.machineState.temperature) * 0.1 + tempDelta;
            }

            // Update pressure with some random variation
            const pressureDelta = (Math.random() - 0.5) * 0.2; // Random change between -0.1 and 0.1
            if (this.machineState.isRunning) {
                this.machineState.pressure = Math.max(
                    0.5,
                    Math.min(5.0, this.machineState.pressure + pressureDelta)
                );
            } else {
                // If not running, tend toward ambient pressure (1.0)
                this.machineState.pressure =
                    this.machineState.pressure + (1.0 - this.machineState.pressure) * 0.1 + pressureDelta;
            }

            // Log current state for debugging
            console.log(
                `Machine state: isRunning=${this.machineState.isRunning}, ` +
                `temperature=${this.machineState.temperature.toFixed(2)}°C, ` +
                `pressure=${this.machineState.pressure.toFixed(2)} bar`
            );
        }, 2000); // Update every 2 seconds
    }

    /**
     * Start the OPC UA server
     */
    async start(): Promise<void> {
        try {
            await this.server.start();
            console.log(
                `OPC UA Server started and listening on port ${SERVER_CONFIG.port}`
            );
            console.log(`Server endpoint: opc.tcp://localhost:${SERVER_CONFIG.port}${SERVER_CONFIG.resourcePath}`);
        } catch (err) {
            console.error("Error starting server:", err);
            throw err;
        }
    }

    /**
     * Stop the OPC UA server and clean up resources
     */
    async stop(): Promise<void> {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
            this.simulationInterval = null;
        }

        try {
            await this.server.shutdown();
            console.log("OPC UA Server stopped");
        } catch (err) {
            console.error("Error stopping server:", err);
            throw err;
        }
    }
}

/**
 * Main function to run the simulator
 */
async function main(): Promise<void> {
    const simulator = new MachineSimulator();

    // Handle shutdown signals for graceful termination
    process.on("SIGINT", async () => {
        console.log("Stopping OPC UA Machine Simulator...");
        await simulator.stop();
        process.exit(0);
    });

    try {
        await simulator.initialize();
        await simulator.start();
        console.log("Machine simulator is running. Press Ctrl+C to stop.");
    } catch (err) {
        console.error("Failed to start simulator:", err);
        process.exit(1);
    }
}

// Run the application
main().catch((err) => {
    console.error("Unhandled error:", err);
    process.exit(1);
});