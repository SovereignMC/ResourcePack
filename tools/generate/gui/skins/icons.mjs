// Control / chapter icon art (16x16 pixel grids of hex colours or null). Ported verbatim from the
// approved controls proposal (ART/COL/TIERS DSL). Shared by generate.mjs (item textures and the
// baked guide_home chapter tiles) so the art is defined once.
export const COL={w:'#ffffff',l:'#c9ccd1',g:'#8a9099',d:'#4c525b',k:'#16181b',
  amber:'#e8a13a',amberD:'#a8661a',green:'#4fcf72',greenD:'#23843f',red:'#e2554a',redD:'#93261f',cyan:'#46c6dd',cyanD:'#1f7f93',blue:'#4f86e8',blueD:'#284f9e',gold:'#e6c25a',goldD:'#9a7a24',brown:'#a8743f',brownD:'#6b4520',purple:'#a571e0',purpleD:'#5e3a8e'};
function grid(){return Array.from({length:16},()=>Array(16).fill(null));}
function P(g,x,y,c){if(x>=0&&x<16&&y>=0&&y<16)g[y][x]=c;}
function rect(g,x0,y0,x1,y1,c){for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)P(g,x,y,c);}
function line(g,x0,y0,x1,y1,c,t=1){const n=Math.max(Math.abs(x1-x0),Math.abs(y1-y0));for(let i=0;i<=n;i++){const x=Math.round(x0+(x1-x0)*i/n),y=Math.round(y0+(y1-y0)*i/n);rect(g,x,y,x+t-1,y+t-1,c);}}
function disc(g,cx,cy,r,c){for(let y=0;y<16;y++)for(let x=0;x<16;x++){const dx=x+.5-cx,dy=y+.5-cy;if(dx*dx+dy*dy<=r*r)P(g,x,y,c);}}
function ring(g,cx,cy,r,t,c,skip){for(let y=0;y<16;y++)for(let x=0;x<16;x++){const dx=x+.5-cx,dy=y+.5-cy,d=Math.sqrt(dx*dx+dy*dy);if(d<=r&&d>r-t&&!(skip&&skip(dx,dy)))P(g,x,y,c);}}
function tri(g,pts,c){const [a,b,d]=pts;for(let y=0;y<16;y++)for(let x=0;x<16;x++){const px=x+.5,py=y+.5;const s=(p,q,r)=>(p[0]-r[0])*(q[1]-r[1])-(q[0]-r[0])*(p[1]-r[1]);const d1=s([px,py],a,b),d2=s([px,py],b,d),d3=s([px,py],d,a);const neg=(d1<0)||(d2<0)||(d3<0),pos=(d1>0)||(d2>0)||(d3>0);if(!(neg&&pos))P(g,x,y,c);}}
const FONT={0:"111101101101111",1:"010110010010111",2:"110001010100111",3:"110001010001110",4:"101101111001001",5:"111100110001110",'?':"110001010000010",'+':"000010111010000",i:"010000010010010"};
function glyph(g,ch,x,y,c,s=1){const f=FONT[ch];for(let j=0;j<15;j++)if(f[j]==='1')rect(g,x+(j%3)*s,y+((j/3)|0)*s,x+(j%3)*s+s-1,y+((j/3)|0)*s+s-1,c);}
function outline(g){const o=grid();for(let y=0;y<16;y++)for(let x=0;x<16;x++){if(g[y][x])continue;for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const nx=x+dx,ny=y+dy;if(nx>=0&&nx<16&&ny>=0&&ny<16&&g[ny][nx]&&g[ny][nx]!==COL.k){o[y][x]=COL.k;break;}}}for(let y=0;y<16;y++)for(let x=0;x<16;x++)if(o[y][x])g[y][x]=o[y][x];return g;}
function flipH(g){return g.map(r=>r.slice().reverse());}
function grey(g){return g.map(r=>r.map(c=>{if(!c||c===COL.k)return c;const v=parseInt(c.slice(1,3),16)*.3+parseInt(c.slice(3,5),16)*.59+parseInt(c.slice(5,7),16)*.11;const t=Math.round(70+v*.35).toString(16).padStart(2,'0');return '#'+t+t+t;}));}

const ART={
 back(){const g=grid();tri(g,[[1,6],[6,1.5],[6,10.5]],COL.amber);rect(g,6,4,12,7,COL.amber);rect(g,10,4,13,12,COL.amber);rect(g,5,10,13,13,COL.amber);rect(g,6,4,12,4,'#f6c77a');rect(g,5,13,13,13,COL.amberD);rect(g,13,5,13,13,COL.amberD);return outline(g);},
 home(){const g=grid();tri(g,[[8,1],[15,8],[1,8]],COL.l);rect(g,3,8,12,14,COL.w);rect(g,7,10,9,14,COL.amber);rect(g,4,9,5,10,COL.g);rect(g,10,9,11,10,COL.g);rect(g,11,2,12,5,COL.d);rect(g,3,14,12,14,COL.l);return outline(g);},
 close(){const g=grid();rect(g,2,2,13,13,COL.d);rect(g,2,2,13,2,COL.g);line(g,4,4,10,10,COL.red,2);line(g,10,4,4,10,COL.red,2);return outline(g);},
 next(){const g=grid();rect(g,1,2,14,13,COL.d);rect(g,1,2,14,2,COL.g);tri(g,[[5,4],[12,8],[5,12]],COL.amber);rect(g,5,4,6,4,'#f6c77a');return outline(g);},
 prev(){return flipH(ART.next());},
 search(){const g=grid();disc(g,6.5,6.5,5.5,COL.w);disc(g,6.5,6.5,3.5,COL.cyan);rect(g,4,4,5,5,'#bdf3ff');line(g,10,10,13,13,COL.g,2);line(g,11,10,14,13,COL.d,1);return outline(g);},
 page(){const g=grid();rect(g,3,1,12,14,COL.w);rect(g,5,4,10,4,COL.g);rect(g,5,7,10,7,COL.g);rect(g,5,10,8,10,COL.g);rect(g,11,1,12,2,COL.l);return outline(g);},
 info(){const g=grid();disc(g,8,8,7,COL.blue);ring(g,8,8,7,1,COL.blueD);rect(g,7,3,8,4,COL.w);rect(g,7,6,8,12,COL.w);rect(g,6,12,9,12,COL.w);return outline(g);},
 charge(n){const g=grid();rect(g,1,4,13,12,COL.d);rect(g,14,6,14,10,COL.g);rect(g,2,5,12,11,'#22262c');const c=n<=1?COL.red:(n===2?COL.amber:COL.cyan);for(let i=0;i<n;i++)rect(g,3+i*2.5|0,6,(3+i*2.5|0)+1,10,c);rect(g,1,4,13,4,COL.g);return outline(g);},
 fuel(){const g=grid();rect(g,3,4,12,14,COL.amber);rect(g,3,4,12,4,'#f6c77a');rect(g,12,5,12,14,COL.amberD);rect(g,5,1,9,3,COL.d);rect(g,10,2,12,3,COL.g);line(g,5,7,10,12,COL.amberD,1);line(g,10,7,5,12,COL.amberD,1);return outline(g);},
 crate(state){const g=grid();rect(g,1,3,12,13,COL.brown);rect(g,1,3,12,3,'#c99257');for(const y of [6,10])rect(g,1,y,12,y,COL.brownD);rect(g,1,3,1,13,COL.brownD);rect(g,12,3,12,13,COL.brownD);
   const c=state==='linked'?COL.green:state==='broken'?COL.red:COL.gold;ring(g,12,12,3.6,1.6,c);if(state==='broken')line(g,10,14,14,10,COL.k,1);return outline(g);},
 mode(){const g=grid();disc(g,8,8,7,COL.l);disc(g,8,8,5,COL.d);line(g,8,8,11,4,COL.amber,2);disc(g,8,8,1.6,COL.w);for(const [x,y] of [[2,8],[8,1],[14,8],[3,3],[13,3]])P(g,x,y,COL.w);return outline(g);},
 power(on){const g=grid();const c=on?COL.green:COL.red;ring(g,8,9,6.5,2,c,(dx,dy)=>dy<-2&&Math.abs(dx)<2.5);rect(g,7,1,8,8,c);return outline(g);},
 repair(){const g=grid();line(g,3,13,10,6,COL.g,2);disc(g,11.5,4.5,3.5,COL.l);rect(g,11,2,13,4,null);P(g,11,4,COL.l);line(g,12,1,14,3,null);rect(g,2,12,4,14,COL.d);return outline(g);},
 pin(on){const g=grid();const c=on?COL.red:COL.g;disc(g,8,5.5,4.5,c);disc(g,7,4.5,1.5,'#ffffff');line(g,8,10,8,15,COL.l,1);if(!on)line(g,2,14,14,2,COL.d,1);return outline(g);},
 deregister(){const g=grid();rect(g,3,4,12,14,COL.l);rect(g,2,2,13,3,COL.g);rect(g,6,1,9,1,COL.g);for(const x of [5,8,11])rect(g,x,6,x,12,COL.g);line(g,2,13,13,2,COL.red,2);return outline(g);},
 tag(){const g=grid();tri(g,[[1,8],[5,3],[5,13]],COL.gold);rect(g,5,3,14,13,COL.gold);rect(g,5,3,14,3,'#f5dc8f');disc(g,4.5,8,1.2,COL.k);rect(g,7,7,12,7,COL.goldD);rect(g,7,10,11,10,COL.goldD);return outline(g);},
 tier(n){const T=TIERS[n];const g=grid();
   rect(g,2,1,13,9,T.f);tri(g,[[2,9],[14,9],[8,15.5]],T.f);
   if(n>=1){rect(g,2,1,13,1,T.h);rect(g,2,1,2,9,T.h);}
   rect(g,13,2,13,9,T.d);
   if(n===0){for(const y of [3,6,9])rect(g,3,y,12,y,T.d);}
   if(n===2){for(const [x,y] of [[3,10],[12,4],[11,11],[3,5]])P(g,x,y,T.pat);}
   if(n>=2){P(g,3,2,T.d);P(g,12,2,T.d);}
   if(n>=3){P(g,3,9,T.d);P(g,12,9,T.d);}
   if(n===5){for(let y=2;y<=9;y++){P(g,3,y,T.trim);P(g,12,y,T.trim);}rect(g,3,2,12,2,T.trim);line(g,3,10,7,14,T.trim,1);line(g,12,10,8,14,T.trim,1);P(g,4,3,'#ffffff');P(g,11,3,'#ffffff');}
   if(n>=4){P(g,7,13,T.gem);P(g,8,13,T.gem);P(g,7,12,T.gem);P(g,8,12,T.gem);}
   glyph(g,String(n),5,2,T.num,2);return outline(g);},
 viewTree(){const g=grid();rect(g,6,1,9,4,COL.w);rect(g,1,11,4,14,COL.w);rect(g,11,11,14,14,COL.w);rect(g,7,5,8,8,COL.l);rect(g,2,8,13,8,COL.l);rect(g,2,8,3,10,COL.l);rect(g,12,8,13,10,COL.l);rect(g,6,1,9,1,COL.amber);return outline(g);},
 viewList(){const g=grid();for(const y of [2,7,12]){rect(g,1,y,3,y+2,COL.amber);rect(g,6,y,14,y+2,COL.w);}return outline(g);},
 viewUsed(){const g=grid();rect(g,7,6,14,14,COL.brown);rect(g,7,6,14,6,'#c99257');rect(g,1,2,7,4,COL.w);tri(g,[[6,0],[10,3],[6,7]],COL.w);return outline(g);},
 lock(){const g=grid();ring(g,8,7,5,2,COL.l,(dx,dy)=>dy>0);rect(g,3,7,12,14,COL.gold);rect(g,3,7,12,7,'#f5dc8f');rect(g,7,9,8,12,COL.k);return outline(g);},
 confirm(){const g=grid();line(g,2,8,6,12,COL.green,3);line(g,6,12,13,3,COL.green,3);return outline(g);},
 layerUp(){const g=grid();for(const [y,c] of [[11,COL.d],[8,COL.g],[5,COL.l]]){tri(g,[[1,y+1.5],[8,y-1.5],[15,y+1.5]],c);tri(g,[[1,y+1.5],[15,y+1.5],[8,y+4.5]],c);}tri(g,[[8,0],[12,4],[4,4]],COL.amber);return outline(g);},
 layerDown(){return ART.layerUp().slice().reverse();},
 empty(){const g=grid();for(let i=1;i<15;i+=2){P(g,i,1,COL.g);P(g,i,14,COL.g);P(g,1,i,COL.g);P(g,14,i,COL.g);}return g;},
 unknown(){const g=grid();rect(g,2,2,13,13,COL.purple);rect(g,2,2,13,2,'#c7a2f0');glyph(g,'?',5,3,COL.w,2);return outline(g);},
 status(){const g=grid();rect(g,2,1,13,14,COL.l);rect(g,2,1,13,1,COL.w);rect(g,4,4,11,8,'#22262c');for(let i=0;i<3;i++)rect(g,5+i*2,5,5+i*2,7,COL.green);rect(g,4,11,7,11,COL.g);disc(g,10.5,11.5,1.5,COL.green);return outline(g);},
 cap(){const g=grid();for(let i=0;i<3;i++)for(let j=0;j<3;j++)rect(g,1+i*5,1+j*5,3+i*5,3+j*5,(i+j*3)<7?COL.w:COL.d);return outline(g);},
 families(){const g=grid();rect(g,2,1,13,14,COL.red);rect(g,2,1,4,14,COL.redD);rect(g,5,3,11,5,COL.w);rect(g,6,12,13,13,COL.l);return outline(g);},
 ticket(){const g=grid();rect(g,1,4,14,11,COL.green);rect(g,1,4,14,4,'#9ce8b0');for(let y=5;y<11;y+=2)P(g,10,y,COL.greenD);glyph(g,'+',3,5,COL.w,1);return outline(g);},
 producer(){const g=grid();rect(g,1,6,14,14,COL.g);tri(g,[[1,6],[5,2],[5,6]],COL.l);tri(g,[[5,6],[9,2],[9,6]],COL.l);rect(g,11,1,13,6,COL.d);rect(g,4,10,6,14,COL.amber);rect(g,9,9,12,11,'#22262c');return outline(g);},
 chStart(){const g=grid();rect(g,3,1,4,15,COL.d);tri(g,[[5,1],[14,4.5],[5,8]],COL.red);return outline(g);},
 chStructures(){const g=grid();rect(g,2,7,13,14,COL.l);tri(g,[[2,7],[7.5,2],[13,7]],COL.g);rect(g,6,10,9,14,COL.d);rect(g,3,9,4,10,COL.cyan);rect(g,11,9,12,10,COL.cyan);rect(g,12,2,13,6,COL.d);return outline(g);},
 chItems(){const g=grid();tri(g,[[1,13],[4,9],[10,9]],COL.gold);rect(g,4,9,10,13,COL.gold);tri(g,[[10,9],[14,13],[10,13]],COL.goldD);rect(g,4,9,10,9,'#f5dc8f');tri(g,[[4,7],[7,3],[12,3]],COL.l);rect(g,7,3,12,7,COL.l);rect(g,7,3,12,3,COL.w);return outline(g);},
 chMilitary(){const g=grid();rect(g,5,5,10,14,COL.gold);tri(g,[[5,5],[7.5,0.5],[10,5]],COL.brown);rect(g,5,12,10,14,COL.goldD);rect(g,5,5,10,5,'#f5dc8f');return outline(g);},
 chMachines(){const g=grid();disc(g,8,8,6.8,COL.g);for(const [x,y] of [[7,0],[7,14],[0,7],[14,7],[2,2],[12,2],[2,12],[12,12]])rect(g,x,y,x+1,y+1,COL.g);disc(g,8,8,3,COL.d);disc(g,8,8,1.4,COL.amber);return outline(g);},
 chReference(){const g=grid();rect(g,2,2,13,13,COL.blue);rect(g,2,2,4,13,COL.blueD);rect(g,5,13,13,14,COL.w);rect(g,6,4,11,6,COL.w);return outline(g);},
};
const TIERS=[
 {f:'#9a6a3c',h:'#c08a52',d:'#6b4520',num:'#2a1a0c'},
 {f:'#8f949b',h:'#c4c9cf',d:'#5c6168',num:'#24272b'},
 {f:'#c87a43',h:'#eaa577',d:'#8a4a22',num:'#2a1408',pat:'#4fae8f'},
 {f:'#d7dde3',h:'#ffffff',d:'#8d969f',num:'#2b3036'},
 {f:'#e6c25a',h:'#fbe39a',d:'#9a7a24',num:'#3a2a00',gem:'#e2554a'},
 {f:'#57d9e6',h:'#c8f8fc',d:'#1f8a99',num:'#0b2a30',gem:'#a571e0',trim:'#e6c25a'}];

// id -> art call + states. Single-state icons have `art` only; multi-state icons list `states`
// (state index = custom_model_data). Mirrors GROUPS in the proposal.
export const CONTROLS = [
  ['back', ['back']], ['home', ['home']], ['close', ['close']], ['search', ['search']],
  ['page_prev', null, [['prev'], ['prev', 'grey']]], ['page_next', null, [['next'], ['next', 'grey']]], ['page_info', ['page']],
  ['charge', null, [0, 1, 2, 3, 4].map(n => ['charge', n])], ['fuel', ['fuel']],
  ['crate', null, [['crate', 'linked'], ['crate', 'linking'], ['crate', 'broken']]], ['mode', ['mode']],
  ['run', null, [['power', true], ['power', false]]], ['repair', ['repair']], ['status', ['status']], ['info', ['info']],
  ['pin', null, [['pin', true], ['pin', false]]], ['nickname', ['tag']], ['deregister', ['deregister']], ['cap', ['cap']],
  ['families', ['families']], ['ticket', ['ticket']], ['confirm', ['confirm']],
  ['view_tree', ['viewTree']], ['view_list', ['viewList']], ['view_used', ['viewUsed']], ['producer', ['producer']],
  ['layer_up', null, [['layerUp'], ['layerUp', 'grey']]], ['layer_down', null, [['layerDown'], ['layerDown', 'grey']]],
  ['lock', ['lock']], ['empty', ['empty']], ['unknown', ['unknown']],
  ...[0, 1, 2, 3, 4, 5].map(t => ['tier_' + t, ['tier', t]]),
  ['ch_start', ['chStart']], ['ch_structures', ['chStructures']], ['ch_items', ['chItems']],
  ['ch_military', ['chMilitary']], ['ch_machines', ['chMachines']], ['ch_reference', ['chReference']],
  ['blank', ['blank']],
];
export function artOf(spec) {
  if (spec[0] === 'blank') return grid();
  if (spec[1] === 'grey') return grey(ART[spec[0]]());
  return ART[spec[0]](...spec.slice(1));
}
export const CHAPTER_ART = { ch_start: ['chStart'], ch_structures: ['chStructures'], ch_items: ['chItems'], ch_military: ['chMilitary'], ch_machines: ['chMachines'], ch_reference: ['chReference'] };
