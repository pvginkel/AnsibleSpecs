# Migration ledger

The test phase's push list for the repos the run does not track itself
([attachments/consumer-files.md](attachments/consumer-files.md) § The ledger). One row per migrated
file; a repo's files share its one commit, its only commit ahead of origin. Nothing here is pushed
before the test phase, and each commit is rebased onto its origin when it is.

| Repo | Job | Clone | Branch | File | Commit |
| --- | --- | --- | --- | --- | --- |
| CalendarDisplay | Firmware/CalendarDisplay | `/work/scratch/CalendarDisplay` | `main` | `Jenkinsfile` | `f2305bccbad14eb3ebf1484f379e59a84e79b6d0` |
| DoorbellReceiver | Firmware/DoorbellReceiver | `/work/scratch/DoorbellReceiver` | `main` | `Jenkinsfile` | `e2c071367fce74b20f57474cc16d091c4bfb3f68` |
| GestureDevice | Firmware/GestureDevice | `/work/scratch/GestureDevice` | `main` | `Jenkinsfile` | `4251d5459599cc5a2126e9970683565b586b934b` |
| InfraStatisticsDisplay | Firmware/InfraStatisticsDisplay | `/work/scratch/InfraStatisticsDisplay` | `main` | `Jenkinsfile` | `8c771ec567e3ab037bf3b2c58c7bf9c90486a02b` |
| Intercom | Firmware/Intercom | `/work/scratch/Intercom` | `main` | `Jenkinsfile` | `4ba47520334cbe2ad76070b992b1a87cdca79c9d` |
| PaperClock | Firmware/PaperClock | `/work/scratch/PaperClock` | `main` | `Jenkinsfile` | `195fc05f3acbe5a6519e33018c1e3bef3cd1607b` |
| ThermostatProxy | Firmware/ThermostatProxy | `/work/scratch/ThermostatProxy` | `main` | `Jenkinsfile` | `9c46c0dc3f726f36ad5243936b4aa114e854cd0f` |
| UnderfloorHeatingController | Firmware/UnderfloorHeatingController | `/work/scratch/UnderfloorHeatingController` | `main` | `Jenkinsfile` | `9e01f6132b078c6e12935b55bbffc1c047845c45` |
| DHCPApp | DHCP/DHCPApp | `/work/scratch/DHCPApp` | `main` | `Jenkinsfile` | `cca07a42086f3d3b8d6e561809ca4f9a7bb986e1` |
| ElectronicsInventory | ElectronicsInventory/ElectronicsInventory | `/work/scratch/ElectronicsInventory` | `main` | `Jenkinsfile` | `4bcc459a6fed3beb474486ce8f121e628e8a5c32` |
| FieldnotesApp | FieldnotesApp | `/work/scratch/FieldnotesApp` | `main` | `Jenkinsfile` | `6f323128a636bc7c93c6c5510d8e7ef06d6f68e1` |
| IoTSupport | IoTSupport/IoTSupport | `/work/scratch/IoTSupport` | `main` | `Jenkinsfile` | `9748ca1580e5bf05b2f0be381f252b41936940cc` |
| IoTSupport | AaC/IoTSupport | `/work/scratch/IoTSupport` | `main` | `Jenkinsfile.architecture` | `9748ca1580e5bf05b2f0be381f252b41936940cc` |
| ZigbeeControl | ZigbeeControl/ZigbeeControl | `/work/scratch/ZigbeeControl` | `main` | `Jenkinsfile` | `f60acf40411fd3808f0331c394a94b405c33db78` |
