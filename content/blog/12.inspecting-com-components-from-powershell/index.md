---
title: 'Inspecting COM+ components from PowerShell'
slug: inspecting-com-components-from-powershell
publishDate: '2024-06-28T09:00:00+01:00'
categories:
- windows
tags:
- tutorial
- networking
- tinkering
- software
- windows
- com
- powershell
image: images/DCOM-overall-architecture.png
---

As part of the datacenter-wide visibility upgrade I'm working on for a [customer](/consulting), I'm setting up monitoring one of their legacy network applications. This application has no logging support whatsoever, and upgrade path available: the original developers have published a new version 10+ years ago, and have no interest for supporting it apart from (sometimes) replying to support tickets. Thus, to set up at least some basic metrics, the solution I came up with is to monitor the COM+ components that work together to make it up.

As a very quick primer, [COM](https://en.wikipedia.org/wiki/Component_Object_Model) (Component Object Model) is an system technology that allows applications to talk to each other using published interfaces, objects, and collections. In practical terms, that means that COM is a specification and a set of implementations that allow different applications to exchange data and function calls. Some other technologies belonging to the same scope that you might have heard of are [CORBA](https://en.wikipedia.org/wiki/Common_Object_Request_Broker_Architecture) and [gRPC](https://grpc.io/). COM also works over a network; in this case, we call it [DCOM](https://en.wikipedia.org/wiki/Distributed_Component_Object_Model) (Distributed COM). If you put COM, DCOM, and a bunch of other Microsoft and Windows tech all together, you get COM+, the [modern Microsoft RPC stack](http://www.indigoo.com/dox/wsmw/1_Middleware/COM.pdf).

### Component Services

Essentially, the customer's application is a client/server application, where the server code sits inside COM+ components, and the client code calls those components to perform CRUD operations. That might sound completely crazy today, but I guess that's how it worked before the whole SOAP craze, that eventually turned into the modern alternatives we use today (including HTTP-based RPC, REST, GraphQL, etc).

Long story short, Windows provides a way to set up those components, making them available over the network for other computers to use. As usual for the COM world, each component gets a GUID. And components are grouped into applications, which are the primary DCOM abstraction. In other words, the client connects to the DCOM/COM+ application, and from there it can use its components remotely.

Windows provides the `comexp.msc`, "Component Services" for friends & family, to inspect, add, and remove applications and components from a Windows system. This utility is essentially a GUI around the [COMAdminCatalog class](https://learn.microsoft.com/en-us/windows/win32/cossdk/comadmincatalog), an admin interface exposed by COM+ to allow the management of applications and components.

This interface contains is big set of related collections, documented [here](https://learn.microsoft.com/en-us/windows/win32/cossdk/com--administration-collections) by Microsoft, which report useful information such as which applications are running and which OS processes are hosting our components.

### Example: measure the number of connected clients

One of the basic metrics I'm deploying as part of the visibility upgrade is the users count. After reflecting for a bit, I figured the easiest way to measure that is to count the number of connections to the COM+ component. This would be a simple matter of filtering the output of `netstat`, if it wasn't for the facts that:

* `netstat` can't distinguish between COM+ components (it just shows them as `dllhost.exe`)
* COM+ just picks a random listen port whenever a component is started

As such, the solutions ended up involving two steps:

1. Find out which process is hosting the COM+ component of interest and its PID. This is done by querying the ApplicationInstances interface, reporting information about running applications. This information includes the PID of the process hosting a given instance. As in this case the customer runs a single instance on each application server, we just filter the list using the GUID of the application of interest, saved in the `$appId` variable.
2. Filter the connections for that PID. First, we get all the active TCP connections. Then, using the PID found in step 1, we filter the list to only get the connections to the specific application.

This has been implemented using PowerShell:

```
$appId = "{F93FACC8-2E16-479B-AA77-6089B1E68588}"  # not the actual GUID

$comAdmin = New-Object -com COMAdmin.COMAdminCatalog

$instances = $comAdmin.GetCollection("ApplicationInstances")
$instances.Populate()
$instances = $instances | Select-Object -Property @{l='CLSID'; e={$_.Value("Application")}}, @{l='PID'; e={$_.Value("ProcessID")}}

$tsInstance = $instances | Where-Object { $_.CLSID -Eq $appId }

$tcpConns = Get-NetTCPConnection |
Where-Object { $_.OwningProcess -Eq $tsInstance.PID } |
Select-Object LocalAddress,
              LocalPort,
              RemoteAddress,
              OwningProcess,
              @{Name="Process";Expression={(Get-Process -Id $_.OwningProcess).ProcessName}}

$specialConns = $tcpConns | Where-Object { $_.RemoteAddress -like "10.15.15.*" }  # count this subnet separately

# Output the number of active connections
Write-Output "0 MagicAppConnections conns=$($tcpConns.Count)|specialConns=$($specialConns.Count) The number of active connections to MagicApp"
```

{{< alert severity="success" >}}
Exercise for the reader: what monitoring/visibility tools accepts the above syntax for a custom metric?
{{< /alert >}}

### Conclusions

COM+ is a gigantic and complex beast, but thanks to an administration interface (also implemented in COM+, of course :) a lot of useful information can be obtained from it. In this article, we have gathered an application-specific metric (the number of connected users) from an otherwise completely opaque COM+ application, using this interface and some creativity.

Please, feel free to [let me know](https://www.bestov.io/about-me) how you're using the COM+ administrative interface. I would be happy to gather and publish some more interesting examples.

Header image credits: [Emerald, P. & Yennun, Chung & Yajnik, Shalini & Liang, Deron & Shih, Joui & Wang, Chung-Yih & Wang, Yi-min. (1998). DCOM and CORBA Side by Side, Step by Step, and Layer by Layer](https://www.ime.usp.br/~reverbel/SOD-97/Textos/dcom_corba/Paper.html).