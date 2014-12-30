#include <wiringPi.h>

#define MOT1 7
#define MOT2 0
#define MOT3 2
#define MOT4 3

int main(void){
	if(wiringPiSetup() == -1)
	return 1;

	pinMode(MOT1, OUTPUT);
	pinMode(MOT2, OUTPUT);
	pinMode(MOT3, OUTPUT);
	pinMode(MOT4, OUTPUT);

	int i;
	for (i=0; i<365; i++){
		digitalWrite(MOT1, 1);
		digitalWrite(MOT2, 0);
		digitalWrite(MOT3, 0);
		digitalWrite(MOT4, 0);
		
		delay(5);

		digitalWrite(MOT1, 0);
		digitalWrite(MOT2, 1);
		digitalWrite(MOT3, 0);
		digitalWrite(MOT4, 0);

		delay(5);

		digitalWrite(MOT1, 0);
		digitalWrite(MOT2, 0);
		digitalWrite(MOT3, 1);
		digitalWrite(MOT4, 0);

		delay(5);

		digitalWrite(MOT1, 0);
		digitalWrite(MOT2, 0);
		digitalWrite(MOT3, 0);
		digitalWrite(MOT4, 1);

		delay(5);

		}
	digitalWrite(MOT1, 0);
	digitalWrite(MOT2, 0);
	digitalWrite(MOT3, 0);
	digitalWrite(MOT4, 0);
	return 0;
}
