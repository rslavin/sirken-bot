-
**!POP**
-
This command updates pop time. Use it when not sure about the ToD.
Pop times are used to calculate eta only if newer than ToD.
-
Simplest way to update a mob (to current date)
```
!pop Lord Bob now
```
Updates some minutes ago
```
!pop Lord Bob 10 minutes ago
```
Updates to a specified time. If time is in the future, yesterday is assumed.
```
!pop Lord Bob 14:01
```
Use different timezones
```
!pop Lord Bob 14:01 est
```
Use the 12hour am/pm time format
```
!pop Lord Bob 02:01pm pst
```
Force the date to yesterday
```
!pop Lord Bob 02:01am yesterday
```
Not sure about the time
```
!pop Lord Bob around 14:00
```
Full date/time
```
!pop Lord Bob 2019-04-20 12:01a.m.
```
```
!pop Lord Bob 2019-04-19 05:00PM pst
```