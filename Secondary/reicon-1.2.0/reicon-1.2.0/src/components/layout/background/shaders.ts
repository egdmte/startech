export const CACHE_KEY = 'reicon-bg-v2';
export const VS = `attribute vec4 p;void main(){gl_Position=p;}`;
export const FS = `
  precision highp float;
  uniform vec2 u_resolution;
  uniform float u_time;
  uniform float u_theme;
  vec3 mod289(vec3 x){return x-floor(x*(1./289.))*289.;}
  vec2 mod289(vec2 x){return x-floor(x*(1./289.))*289.;}
  vec3 permute(vec3 x){return mod289(((x*34.)+1.)*x);}
  float snoise(vec2 v){
    const vec4 C=vec4(.211324865405187,.366025403784439,-.577350269189626,.024390243902439);
    vec2 i=floor(v+dot(v,C.yy));
    vec2 x0=v-i+dot(i,C.xx);
    vec2 i1=(x0.x>x0.y)?vec2(1.,0.):vec2(0.,1.);
    vec4 x12=x0.xyxy+C.xxzz;
    x12.xy-=i1;
    i=mod289(i);
    vec3 pv=permute(permute(i.y+vec3(0.,i1.y,1.))+i.x+vec3(0.,i1.x,1.));
    vec3 m=max(.5-vec3(dot(x0,x0),dot(x12.xy,x12.xy),dot(x12.zw,x12.zw)),0.);
    m=m*m;m=m*m;
    vec3 x=2.*fract(pv*C.www)-1.;
    vec3 h=abs(x)-.5;
    vec3 ox=floor(x+.5);
    vec3 a0=x-ox;
    m*=1.79284291400159-.85373472095314*(a0*a0+h*h);
    vec3 g;
    g.x=a0.x*x0.x+h.x*x0.y;
    g.yz=a0.yz*x12.xz+h.yz*x12.yw;
    return 130.*dot(m,g);
  }
  void main(){
    vec2 st=gl_FragCoord.xy/u_resolution.xy;
    vec2 asp=st; asp.x*=u_resolution.x/u_resolution.y;
    float t=u_time*0.1200;
    vec2 uv=st;
    float w1=snoise(asp*1.5+vec2(t*.4,t*.3));
    float w2=snoise(asp*1.995-vec2(t*.2,t*.5));
    uv.x+=w1*0.25;
    uv.y+=w2*0.25;
    vec3 cBg = mix(vec3(0.9608, 0.9608, 0.9412), vec3(0.0), u_theme);
    vec3 cCyan  = mix(vec3(0.82, 0.92, 0.89), vec3(0.0), u_theme);
    vec3 cOrange= mix(vec3(1.0, 0.83, 0.76), vec3(0.0), u_theme);
    vec3 cYellow= mix(vec3(0.98, 0.82, 0.60), vec3(0.4039, 0.3922, 0.9490), u_theme);
    vec3 cPurple= mix(vec3(0.93, 0.65, 0.77), vec3(0.55, 0.10, 0.80), u_theme);
    vec3 cBlue  = mix(vec3(0.66, 0.77, 1.0), vec3(0.10, 0.25, 0.90), u_theme);
    float n1=snoise(uv*1.2+vec2(t,0.))*.5+.5;
    float n2=snoise(uv*1.5-vec2(0.,t*.6))*.5+.5;
    float n3=snoise(uv*1.3+vec2(-t*.5,t*.3))*.5+.5;
    vec3 bg=mix(cCyan,cBlue,clamp(uv.x+n1*.4,0.,1.));
    bg=mix(bg,cYellow,smoothstep(.2,.9,n2*(1.2-uv.x)*uv.y));
    bg=mix(bg,cPurple,smoothstep(.1,.8,n1*uv.x*(1.1-uv.y)));
    bg=mix(bg,cOrange,smoothstep(.3,1.,n3*(1.-uv.y)*uv.x*1.5));
    float grain=fract(sin(dot(gl_FragCoord.xy+u_time*100.,vec2(12.9898,78.233)))*43758.5453123);
    float grainStrength = mix(0.015, 0.04, u_theme);
    gl_FragColor=vec4(bg+(grain-.5)*grainStrength,1.);
  }
`;
