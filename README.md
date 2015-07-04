# ShareBikeAlert

ShareBikeAlert is a Python script tool providing DC Sharebike data entrance and alert.

It happens sometimes that I want to find a dock for my share bike while the station is full, or the opposite that there's no bike when I get to the station. So there's ShareBikeAlert. It will send you an email or SMS if there's no bike/dock in your station during your chosen time frame.

# Usage

Retrieve closest bike station:
```
bike = BikeShareDC()
bike.get_station('1600 pennsylvania ave NW, washington, DC')
```

Retrieve station data:
```
bike.get_station_info(31011)
```

Set up alert:
In conf.json, we set that if the number of bike is less than 1 in station 31011 during 8AM to 9:15AM, send me an alert.

Using `get_station()` and `get_station_info()` functions to get the station ID, or visit the BikeShare map [https://secure.capitalbikeshare.com/map/](https://secure.capitalbikeshare.com/map/).
```
"jobs": [
    {
      "Start": "08:00:00",
      "End": "09:15:00",
      "StationID": "31011",
      "BikeLessThan": 1,
      "DockLessThan": 0
    }
}
```

Call the class and run.
```
bike.set_alert()
```

Setting up a cron job to run the alert regularly.
