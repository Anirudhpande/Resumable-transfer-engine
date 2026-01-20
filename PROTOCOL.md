## 1. Overview

This document defines Protocol Version 1 for a resumable, chunk-based file transfer system.

The protocol is designed to reliably transfer large directory structures (such as games) between two machines over a network connection, without relying on external storage devices.

The protocol operates at the application layer and assumes a reliable byte-stream transport provided by TCP. All higher-level behavior such as chunking, resuming, integrity verification, and error handling is explicitly defined by this protocol.


## 2. Roles

The protocol defines two roles:

### Receiver
The receiver initiates the transfer and acts as the authoritative controller of the protocol.  
It decides which metadata and file chunks are required, maintains transfer state, and verifies data integrity.

### Sender
The sender provides directory metadata and file data in response to receiver requests.  
The sender never sends unsolicited data and does not control transfer order.

The receiver-driven design ensures resumability, precise control, and predictable recovery from failures.


## 3. Communication Model

The protocol follows a simple one-to-one communication model:

- One sender
- One receiver
- One persistent TCP connection per transfer session

The connection is established by the sender connecting to the receiver, which listens on a known port.

All messages are exchanged sequentially over a single connection.  
The protocol assumes blocking I/O and does not rely on parallel or asynchronous message streams.


## 4. Message Format & Framing

All protocol messages are transmitted over a TCP byte stream. Since TCP does not preserve message boundaries, explicit framing is required.

### Framing Rule

Every message follows a length-prefixed framing format:

[4 bytes MESSAGE_LENGTH][MESSAGE_PAYLOAD]

- MESSAGE_LENGTH is a 32-bit integer in network byte order (big-endian)
- MESSAGE_PAYLOAD is exactly MESSAGE_LENGTH bytes long

The receiver must first read MESSAGE_LENGTH and then read exactly MESSAGE_LENGTH bytes to obtain one complete message.

### Message Encoding

- All control messages are encoded as JSON
- Binary data may follow JSON headers where explicitly defined by a message type
- Raw file data is transmitted as binary bytes without additional encoding

This framing rule applies uniformly to all messages exchanged under this protocol.


## 5. Message Types

This section defines all valid messages in Protocol Version 1.
Any message not defined here is considered a protocol violation.

### MANIFEST_REQUEST

**Sent by:** Receiver → Sender  
**Purpose:** Request the full directory manifest from the sender.

#### Fields
- type: "MANIFEST_REQUEST"

#### Notes
- This message contains no file paths or chunk information.
- It is always the first transfer-related message sent by the receiver.

### MANIFEST_RESPONSE

**Sent by:** Sender → Receiver  
**Purpose:** Provide the complete directory structure and file metadata.

#### Fields
- type: "MANIFEST_RESPONSE"
- root (string): root folder name
- chunk_size (int): size of each chunk in bytes
- files (list):
  - path (string): relative file path
  - size (int): file size in bytes
  - total_chunks (int): number of chunks
  - modified_time (int): unix timestamp

### CHUNK_REQUEST

**Sent by:** Receiver → Sender  
**Purpose:** Request a specific chunk of a specific file.

#### Fields
- type: "CHUNK_REQUEST"
- path (string): relative file path
- chunk_index (int): index of the chunk (0-based)

#### Rules
- Only one chunk may be requested at a time.
- chunk_index must satisfy: 0 ≤ chunk_index < total_chunks.
- The chunk size is determined by the manifest.

### CHUNK_RESPONSE

**Sent by:** Sender → Receiver  
**Purpose:** Send the requested chunk along with integrity metadata.

#### JSON Header Fields
- type: "CHUNK_RESPONSE"
- path (string): relative file path
- chunk_index (int): index of the chunk
- chunk_size (int): size of the chunk in bytes
- hash (string): SHA-256 hash of the chunk data

#### Payload
- Raw binary chunk data immediately following the JSON header.

#### Notes
- The receiver must verify the chunk hash before accepting the data.
- Chunk data is sent only in response to a CHUNK_REQUEST.

### TRANSFER_COMPLETE

**Sent by:** Receiver → Sender  
**Purpose:** Indicate that all required chunks have been successfully received.

#### Fields
- type: "TRANSFER_COMPLETE"

#### Notes
- After sending this message, the receiver will close the connection.
- The sender should treat this as the end of the transfer session.

### ERROR

**Sent by:** Sender or Receiver  
**Purpose:** Indicate a protocol or transfer error.

#### Fields
- type: "ERROR"
- message (string): human-readable error description

#### Notes
- Upon receiving an ERROR, the connection should be closed.
- Recovery, if possible, is handled by restarting the session.


## 6. Transfer Flow

This section defines the valid sequence of message exchanges during a normal transfer session.

The protocol follows a strictly receiver-driven flow. The sender never initiates transfer actions and only responds to explicit receiver requests.

### 6.1 Connection Establishment

1. The receiver starts and listens on a predefined TCP port.
2. The sender initiates a TCP connection to the receiver.
3. Once the connection is established, the protocol session begins.

### 6.2 Manifest Exchange

1. The receiver sends a MANIFEST_REQUEST message.
2. The sender responds with a MANIFEST_RESPONSE message.
3. The receiver parses the manifest and determines the set of required file chunks.

### 6.3 Chunk Transfer Loop

1. The receiver selects a missing or corrupted chunk.
2. The receiver sends a CHUNK_REQUEST message specifying the file path and chunk index.
3. The sender responds with a CHUNK_RESPONSE message containing:
   - A JSON header with chunk metadata and hash
   - The corresponding raw binary chunk data
4. The receiver verifies the chunk integrity using the provided hash.
5. If verification succeeds, the receiver updates its manifest.
6. If verification fails, the receiver re-requests the same chunk.
7. Steps 1–6 repeat until all required chunks are successfully received.

### 6.4 Transfer Completion

1. When no required chunks remain, the receiver sends a TRANSFER_COMPLETE message.
2. The sender acknowledges completion implicitly by closing the connection.
3. The receiver closes the connection after sending TRANSFER_COMPLETE.

### 6.5 Error Handling During Transfer

- If either side encounters a protocol violation or unrecoverable error, it sends an ERROR message.
- Upon sending or receiving an ERROR message, the connection must be closed immediately.
- Recovery, if possible, occurs by restarting the protocol session using persisted receiver state.

### Protocol Invariants

The following conditions must always hold:

- The sender never sends data without an explicit request.
- Only one chunk is in flight at any time.
- The receiver is the only entity that decides transfer order.
- A chunk is immutable once its hash is published in MANIFEST_RESPONSE.
- Sender and receiver must never assume shared filesystem state.


## 7. Failure & Resume Semantics

The protocol is designed with the assumption that failures are normal and expected.

### Chunk Hash Semantics

- The sender computes SHA-256 hashes for all chunks when responding to MANIFEST_REQUEST.
- Chunk hashes are included in MANIFEST_RESPONSE.
- These hashes represent the expected content of each chunk.
- During transfer, the sender also includes the hash in CHUNK_RESPONSE.
- The receiver verifies that the received chunk hash matches the expected hash
  from the manifest.
- If verification fails, the receiver re-requests the chunk.


### Failure Scenarios

Failures may include, but are not limited to:
- Network disconnections
- Sender or receiver process crashes
- System restarts
- Chunk corruption or incomplete transmission

### Failure Handling Rules

- The receiver maintains a persistent manifest that records completed chunks.
- The sender maintains no transfer state between sessions.
- Upon any connection failure, both sides must discard in-memory transfer state.
- No attempt is made to continue a session after a protocol error or disconnection.
- If a CHUNK_RESPONSE is received for a chunk that was not requested,
  the receiver must treat this as a protocol violation and send ERROR.
- If a chunk hash verification fails, the receiver must re-request the
  same chunk and must not advance transfer state.
- If the TCP connection drops at any point, both sender and receiver
  must discard in-memory state and close the connection.
- The receiver must never mark a chunk as completed unless its hash
  verification succeeds.
- The sender must not cache or reuse chunk data across sessions.


### Resume Behavior

1. The receiver restarts and reloads its local manifest.
2. A new protocol session is established.
3. The receiver requests the manifest again.
4. The receiver requests only missing or corrupted chunks.
5. Already completed chunks are never re-requested.

This design guarantees safe and deterministic resumption without duplicate or unnecessary data transfer.


## 8. Protocol Versioning

This document defines Protocol Version 1.

### Version Identification

- Both sender and receiver are assumed to implement Protocol Version 1.
- Version negotiation is not required for this version.

### Future Compatibility

- Future protocol versions may extend message types or fields.
- Backward-incompatible changes must be introduced under a new protocol version.
- Protocol Version 1 is intentionally minimal and strict to ensure correctness and simplicity.


## 9. State Machines

This part defines all the possible filesystem states.
### Receiver States

- INIT  
  Receiver is started but no connection exists.
- CONNECTED  
  TCP connection established with sender.
- WAITING_FOR_MANIFEST  
  MANIFEST_REQUEST sent, awaiting MANIFEST_RESPONSE.
- REQUESTING_CHUNKS  
  Receiver selects missing chunks and sends CHUNK_REQUEST messages.
- VERIFYING_CHUNK  
  Receiver verifies hash of received chunk and updates manifest.
- COMPLETED  
  All chunks verified; TRANSFER_COMPLETE sent.
- ERROR  
  Protocol violation or unrecoverable error encountered.

### Sender States

- IDLE  
  Sender not connected.
- CONNECTED 
  TCP connection established.
- SENDING_MANIFEST  
  Responding to MANIFEST_REQUEST.
- SENDING_CHUNK  
  Responding to CHUNK_REQUEST.
- TERMINATED  
  Connection closed or TRANSFER_COMPLETE received.
