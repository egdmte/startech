_state = 'TUMSEK' # Simulation state variable
l = 70
r = 50
SPEED_BUMP_SPEED = 25

import controller
if _state != 'TUMSEK':
    # do a random stuff, since this condition will not run
    print("uWu")
elif _state == 'TUMSEK':
    
    scale = SPEED_BUMP_SPEED / max(abs(l), abs(r), 1)
    print(l * scale, r * scale, "Less than dead zone:", 30>abs(l * scale), 30>abs(r * scale))
    print("Car stops at speed bump" if 30>abs(l * scale) and 30>abs(r * scale) else "Car continues moving")

