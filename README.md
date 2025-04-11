# NetWolf P2P File Sharing System

NetWolf is a peer-to-peer file sharing system built using raw socket programming in Python. It enables nodes to join a distributed cluster, discover peers dynamically, send file requests, and transfer files over the network using a combination of UDP and TCP communication.

## Implemented Features

### 1. Cluster Initialization and Discovery
Each node starts with a list of known peers. Nodes periodically send discovery messages over UDP to share and update their view of the cluster. The discovery protocol ensures that all active peers are aware of each other by merging and broadcasting updated lists.

### 2. File Request Propagation
Nodes can request files using a custom `get` command. The request is propagated across the cluster using UDP. Each node that holds the requested file responds with its availability and delay metrics.

### 3. Delay-Based Selection
To optimize performance, the requesting node waits for responses within a predefined time window and selects the node with the lowest response delay to initiate the file transfer.

### 4. File Transfer via TCP
File transfers are conducted over TCP sockets. Once the best responder is selected, a direct TCP connection is established for reliable file transmission. Nodes listen on randomly assigned TCP ports and include port information in their responses.

### 5. Load Distribution
Nodes monitor their load and limit the number of concurrent transfers. If a node is actively serving too many requests, it temporarily stops responding to new ones to avoid bandwidth congestion.

### 6. Free Rider Mitigation
Nodes track prior communication history and introduce artificial delays in their responses if they have not previously contributed. This discourages one-sided usage of the system.

### 7. Concurrent Service Handling
Each node concurrently handles UDP discovery, file request processing, and TCP transfers using threads. All three services run in parallel to support real-time operation.

### 8. Protocol and Configuration
All communication protocols are custom-built. Serialization and deserialization are manually handled. Nodes are configured through command-line parameters, allowing runtime flexibility in setting cluster files, shared directories, and listening ports.

## Notes
- File lookup is based on filename only; there is no content-based search.
- Communication is strictly limited to low-level socket operations.
- No third-party libraries are used for networking or message formatting.
