# BGPgeopolitics
This is a BGP ammouncement flagging tool that augment incoming BGP updates feed with different type of infomations. The
tool is written in python and is maintained at https://github.com/ksalamat/BGPgeopolitics. The tools leverage on BGPstream
library (bgpstream.caida.org) to access BGP sources and extract BGP informations in readable format. A JSON format of the
BGP updates is generated that is similar to the one used in exabgp (https://github.com/Exa-Networks/exabgp) enabling easy
interfacing with exabg routers. The JSON is augmented therafter through a database (stored by default in the resources/
directory), that contains AS country information along with historical security, performance and geopolitical risk indices.
This results into three main outcomes:
1-an augmented BGP annoucement repository that contain BGP announcements in JSON format with the the additional flags , eg.,
{
    'peer': {'address': '198.32.160.137', 'asn': 19151},
    'flags': {
        'category': 'AADup',
        'risk': 0.981082381938982,
        'geoPath': ['US', 'US', 'UA', 'UA']
    },
    'time': 1438500057,
    'fields': {'nextHop': '198.32.160.137',
    'asPath': ['19151', '174', '13188', '200013'],
    'prefix': '185.38.217.0/24'},
    'message': 'announce'
}
that says that the BGP announcement is a AADUP (Implicit withdrawal of a route and replacement by route that is identical
in all path attributes., that it involve an overall risk value of 0.98 and that its paths goes from US to Ukraine (UA).

2- A BGP table containing for each prefix (both IPv4 and IPv6) all paths announced along with the flags and performance
informations like number of flaps, oe AADup, AADiff, WADup and WADiff and average up and down times.
 eg.
 "209.186.254.0/24": {
    "prefix": "209.186.254.0/24",
    "announcements": 5,
    "flaps": 2,
    "AADup": 0,
    "AADiff": 0,
    "WADiff": 2,
    "WADup": 0},
    "WWDup": 0,
    "paths": [
        {
            "active": true,
            "meanDown": 1.35,
            "meanUp": 4.86,
            "risk": 0.020168598934496452,
            "nextHop": "198.32.160.103",
            "lastChange": 1438500060,
            "peerASn": 13030,
            "path": ["13030", "1299", "7018", "26789"],
            "geoPath": ["CH", "EU", "US", "US"]
         }
         {
            "active": false,
            "meanDown": 0.9000000000000001,
            "meanUp": 4.59,
            "risk": 0.0012771399111035718,
            "nextHop": "198.32.160.103",
            "lastChange": 1438500032,
            "peerASn": 13030,
            "path": ["13030", "1299", "209", "3908", "721", "26789"],
            "geoPath": ["CH", "EU", "US", "US", "US", "US"]
         },
    ],
 }

 3- A routing table that store for each prefix the best path measured based on minimal risk

 Flagged annoucements are stored in mongodb no-sql database (table BGPdump). The BGP  and  Routing tables are also stored
 monbgodb (table TableDump).

 # INSTALLATION
 The installation can be done in two way: using docker image at ksalamatian/bgpprojectbuild, or as standalone.

#1- Docker Install
 First install the `Docker` environment. You can follow the description here `https://docs.docker.com/engine/installation/`.
After installing Docker execute : `docker pull ksalamatian/bgpprojectbuild:latest` to download the docker image. The docker
image has preinstalled all need components.
Run the docker image : `docker run -i -t ksalamatian/bgpprojectbuild:latest /bin/bash` to open a shell into the docker.

1- In the opened shell execute `mongod -smallfiles &` to launch mongod deamon.

2- set the LD_LIBRARY_PATH, `LD_LIBRARY_PATH=/usr/local/lib` followed by `export LD_LIBRARY_PATH`

3- launch the pyenv into bgpProject directory `source bgpProject/bin/activate`

4- Go to bgpProject/BGPgeopolitics/ and update the python code : "git pull"

4- Go to bgpProject/BGPgeopolitics/ directory and launch `python routeprocess.py -start_time  -c 'rrc11' -start_time 438500000 -end_time 438500600`
The -c parameter defines the collector and the -start_time and -end_time beginning and end of collections in unix time.

#2- Stand Alone install

1- install mongodb

2- install sqlite3

3- install bgpstream (look at https://bgpstream.caida.org/docs/install/bgpstream)

4- install pyenv

5- install python dependencies

6- Follow the steps above.

