# RPA Land Use Model Diagram

```mermaid
graph LR
    %% Data nodes (yellow ovals)
    PRISM["PRISM Historical<br/>Climate"]:::data
    NetReturns["Net Returns to Land<br/>Production"]:::data
    SoilQuality["Soil Quality (NRI)"]:::data
    MACA["MACA Climate<br/>Projections"]:::data
    SSP["Downscaled SSP<br/>Projections"]:::data
    
    %% Ricardian Climate Functions box
    subgraph RCF["Ricardian Climate Functions"]
        Forest["Forest"]:::process
        Crop["Crop"]:::process
        Urban["Urban"]:::process
    end
    
    %% Process nodes (gray rectangles)
    LandUseModel["Land-use<br/>Change Model"]:::process
    
    %% Output nodes (red hexagons)
    ClimateParam["Climate<br/>Parameterized<br/>Net Returns"]:::output
    Transition["Transition<br/>Probability as<br/>Function of<br/>Climate / SSP"]:::output
    SimulatedChange["Simulated Land<br/>Area Change<br/>(Gross & Net)"]:::output
    
    %% Simplified connections to the RCF box
    PRISM --> RCF
    NetReturns --> RCF
    SoilQuality --> RCF
    
    %% Connections from RCF components to other nodes
    Forest --> ClimateParam
    Crop --> ClimateParam
    Urban --> ClimateParam
    
    ClimateParam --> LandUseModel
    LandUseModel --> Transition
    MACA --> Transition
    SSP --> Transition
    
    Transition --> SimulatedChange
    
    %% Styling
    classDef data fill:#ffecb3,stroke:#333,stroke-width:2px
    classDef process fill:#e0e0e0,stroke:#333,stroke-width:2px
    classDef output fill:#ffcdd2,stroke:#333,stroke-width:2px,shape:hexagon
    style RCF fill:#fff5e6,stroke:#be9b3e,stroke-width:3px
```

This diagram represents the RPA Land Use Model's data flow and components, showing how various inputs like climate data and soil quality flow through the Ricardian Climate Functions and ultimately produce simulated land area changes. 