# SupervisedFermentor
CrafBeerPi addon for a Fermentation logic with email notificacion of out of range temp


This addon is a new fermentation logic that monitors ferm temp and send email if it goes out of range.

There is a repetition time for sending the alarm again.

It also have the logic to check on boot if a fermentor have an active step runnig and put it on Automatic.
This option is selectable from a global Parameter .

For sending the email several globa parmas are needed, as email server, user, pass and email destination of the alarm.
