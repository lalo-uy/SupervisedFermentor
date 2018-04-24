from modules import cbpi
from modules.core.controller import KettleController, FermenterController
from modules.core.props import Property
import time
from time import localtime, strftime
import smtplib
import requests


@cbpi.fermentation_controller
class SupervHysteresis(FermenterController):

    heater_offset_min = Property.Number("Heater Offset ON", True, 0, description="Offset as decimal number when the heater is switched on. Should be greater then 'Heater Offset OFF'. For example a value of 2 switches on the heater if the current temperature is 2 degrees below the target temperature")
    heater_offset_max = Property.Number("Heater Offset OFF", True, 0, description="Offset as decimal number when the heater is switched off. Should be smaller then 'Heater Offset ON'. For example a value of 1 switches off the heater if the current temperature is 1 degree below the target temperature")
    cooler_offset_min = Property.Number("Cooler Offset ON", True, 0, description="Offset as decimal number when the cooler is switched on. Should be greater then 'Cooler Offset OFF'. For example a value of 2 switches on the cooler if the current temperature is 2 degrees above the target temperature")
    cooler_offset_max = Property.Number("Cooler Offset OFF", True, 0, description="Offset as decimal number when the cooler is switched off. Should be less then 'Cooler Offset ON'. For example a value of 1 switches off the cooler if the current temperature is 1 degree above the target temperature")
    super_active = Property.Select("Active supervision", options=["No","Yes"], description="Supervision on this Fermenter ON/OFF")
    max_temp_off = Property.Number("Max Alowed temp error", True, 0, description="Max temp offset alarm threshold")
    min_temp_off = Property.Number("Min Alowed temp error", True, 0, description="Min temp offset alarm threshold")
    rep_time = Property.Number("Repetition time", True, 0, description="Repetition time of alarmemail (0 no repetition)")
    alarmed = 0
    alarm_time = 0

    def stop(self):
        super(FermenterController, self).stop()

        self.heater_off()
        self.cooler_off()

    def run(self):
        while self.is_running():
        
            target_temp = self.get_target_temp()
            temp = self.get_temp()

            if temp + float(self.heater_offset_min) <= target_temp:
                self.heater_on(100)

            if temp + float(self.heater_offset_max) >= target_temp:
                self.heater_off()

            if temp >= target_temp + float(self.cooler_offset_min):
                self.cooler_on(100)

            if temp <= target_temp + float(self.cooler_offset_max):
                self.cooler_off()

            if self.super_active) == "Yes":
 		if abs(temp - target_temp) > float(self.max_temp_off) and self.alarmed == 0:
                	self.alarm_time=time.time()
                	self.alarmed = 1

 		if abs(temp - target_temp) < float(self.min_temp_off) and self.alarmed == 1:
                	self.alarm_time=0
                	self.alarmed = 0


            self.sleep(1)




@cbpi.backgroundtask(key="Ferm_Supervisor", interval=60)
def ferm_supervisor_background_task(a):

    auto_start = cbpi.cache['config']["auto_start"].value
    for key, value in cbpi.cache.get("fermenter").iteritems():
        #print key, "   ", value.name
        if hasattr(value, 'instance'):
            #print value.instance.alarmed
            if value.instance.alarmed == 1 and  value.instance.alarm_time < time.time():
                   # set time for next notificacion
                if value.instance.rep_time > 0 :
                   value.instance.alarm_time = time.time() + float(value.instance.rep_time)*60
                else:
                   # or never notify again
                   value.instance.rep_time = 999999999999

		stemp = cbpi.cache['sensors'][int(value.sensor)].instance.last_value

                server = smtplib.SMTP(cbpi.cache['config']['mail_server'].value, int(cbpi.cache['config']['mail_port'].value))
                server.starttls()
                server.login(cbpi.cache['config']['mail_user'].value, cbpi.cache['config']['mail_psw'].value)
 
                msg = "Subject: CraftBeerPi Alarm \r\n\r\n Alarm on "+value.name+" temp "+stemp.__str__()+"  at "+strftime("%H:%M:%S on %Y %b %d ", localtime())
                server.sendmail(cbpi.cache['config']['mail_user'].value, cbpi.cache['config']['mail_dest'].value, msg)
                server.quit()


        if auto_start == 'Yes' and (not value.state) and len(value.steps) > 0:
            for step in value.steps:
                if step.state == "A":
                    print "arrancar ", key, step.state
                    try:
                        print value.state
                        # Start controller
                        if value.logic is not None:
                            cfg = value.config.copy()
                            cfg.update(
                              dict(api=cbpi, fermenter_id=value.id, heater=value.heater, sensor=value.sensor))
                            instance = cbpi.get_fermentation_controller(value.logic).get("class")(**cfg)
                            instance.init()
                            value.instance = instance

                            def run(instance):
                                instance.run()

                            t = cbpi.socketio.start_background_task(target=run, instance=instance)
                        value.state = not value.state
                        cbpi.emit("UPDATE_FERMENTER", key)
                    except Exception as e:
                        print e
                        cbpi.notify("Toogle Fementer Controller failed", "Pleae check the %s configuration" % value.name,
                            type="danger", timeout=None)



            pass

    pass



@cbpi.initalizer(order=0)
def initFermSupervisor(app):

    mail_server = app.get_config_parameter("mail_server",None)
    if mail_server is None:
        mail_server = "smtp.gmail.com"
        cbpi.add_config_parameter("mail_server", "smtp.gmail.com", "text", "Mail smtp server")

    mail_port = app.get_config_parameter("mail_port",None)
    if mail_port is None:
        mail_port = 587
        cbpi.add_config_parameter("mail_port", 587, "number", "Mail smtp port")

    mail_user = app.get_config_parameter("mail_user",None)
    if mail_user is None:
        mail_user = "your_mail_user"
        cbpi.add_config_parameter("mail_user", "your_mail_user", "text", "Mail user")

    mail_psw = app.get_config_parameter("mail_psw",None)
    if mail_psw is None:
        mail_psw = "your_mail_pass"
        cbpi.add_config_parameter("mail_psw", "your_mail_pass", "text", "Mail psw")

    mail_dest = app.get_config_parameter("mail_dest",None)
    if mail_dest is None:
        mail_dest = "your_mail_destinatio"
        cbpi.add_config_parameter("mail_dest", "your_mail_destinatio", "text", "Mail destinatio")

    auto_start = app.get_config_parameter("auto_start",None)
    if auto_start is None:
        auto_start = "No"
        cbpi.add_config_parameter("auto_start", "No", "select", "Auto start fermenters with active steps on boot", options=["No","Yes"])




