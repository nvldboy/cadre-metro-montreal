const fs = require("fs");

const W = 457.2;
const H = 609.6;
const OUT = "metro-montreal-18x24-led-12mm.svg";
const DRILL = "metro-montreal-18x24-percage-12mm.svg";

const lines = {
  green: {
    color: "#00A651",
    names: ["Angrignon","Monk","Jolicoeur","Verdun","De l’Église","LaSalle","Charlevoix","Lionel-Groulx","Atwater","Guy-Concordia","Peel","McGill","Place-des-Arts","Saint-Laurent","Berri-UQAM","Beaudry","Papineau","Frontenac","Préfontaine","Joliette","Pie-IX","Viau","Assomption","Cadillac","Langelier","Radisson","Honoré-Beaugrand"],
    anchors: [
      {i:0,p:[72,520]}, {i:7,p:[205,432]}, {i:14,p:[286,310]}, {i:26,p:[392,90]}
    ],
    routes: [
      [[72,520],[118,490],[162,458],[205,432]],
      [[205,432],[232,395],[258,352],[286,310]],
      [[286,310],[320,275],[345,230],[368,165],[392,90]]
    ]
  },
  orange: {
    color: "#F58220",
    names: ["Côte-Vertu","Du Collège","De la Savane","Namur","Plamondon","Côte-Sainte-Catherine","Snowdon","Villa-Maria","Vendôme","Place-Saint-Henri","Lionel-Groulx","Georges-Vanier","Lucien-L’Allier","Bonaventure","Square-Victoria–OACI","Place-d’Armes","Champ-de-Mars","Berri-UQAM","Sherbrooke","Mont-Royal","Laurier","Rosemont","Beaubien","Jean-Talon","Jarry","Crémazie","Sauvé","Henri-Bourassa","Cartier","De la Concorde","Montmorency"],
    anchors: [
      {i:0,p:[72,72]}, {i:6,p:[120,340]}, {i:10,p:[205,432]}, {i:17,p:[286,310]}, {i:23,p:[245,185]}, {i:30,p:[360,68]}
    ],
    routes: [
      [[72,72],[96,145],[102,250],[120,340]],
      [[120,340],[148,372],[176,405],[205,432]],
      [[205,432],[226,405],[248,370],[268,338],[286,310]],
      [[286,310],[274,270],[262,225],[245,185]],
      [[245,185],[276,145],[315,105],[360,68]]
    ]
  },
  blue: {
    color: "#0072BC",
    names: ["Snowdon","Côte-des-Neiges","Université-de-Montréal","Édouard-Montpetit","Outremont","Acadie","Parc","De Castelnau","Jean-Talon","Fabre","D’Iberville","Saint-Michel"],
    anchors: [
      {i:0,p:[120,340]}, {i:8,p:[245,185]}, {i:11,p:[342,155]}
    ],
    routes: [
      [[120,340],[145,310],[155,265],[176,225],[210,198],[245,185]],
      [[245,185],[278,176],[310,164],[342,155]]
    ]
  },
  yellow: {
    color: "#FFD200",
    names: ["Berri-UQAM","Jean-Drapeau","Longueuil–Université-de-Sherbrooke"],
    anchors: [
      {i:0,p:[286,310]}, {i:2,p:[408,337]}
    ],
    routes: [
      [[286,310],[346,310],[375,330],[408,337]]
    ]
  }
};

function dist(a,b){ return Math.hypot(b[0]-a[0],b[1]-a[1]); }
function pointOnPolyline(poly, t) {
  const lengths = poly.slice(1).map((p,i)=>dist(poly[i],p));
  const total = lengths.reduce((a,b)=>a+b,0);
  let target = t*total;
  for(let i=0;i<lengths.length;i++){
    if(target <= lengths[i]){
      const q = lengths[i] ? target/lengths[i] : 0;
      return [
        poly[i][0] + (poly[i+1][0]-poly[i][0])*q,
        poly[i][1] + (poly[i+1][1]-poly[i][1])*q
      ];
    }
    target -= lengths[i];
  }
  return poly[poly.length-1];
}

for (const line of Object.values(lines)) {
  line.points = [];
  for (let s=0;s<line.anchors.length-1;s++) {
    const a=line.anchors[s], b=line.anchors[s+1], count=b.i-a.i;
    for(let j=0;j<=count;j++){
      if(s>0 && j===0) continue;
      line.points[a.i+j]=pointOnPolyline(line.routes[s],j/count);
    }
  }
}

const esc = s => s.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
const fmt = n => Number(n.toFixed(2));
const polyPoints = route => route.map(p=>`${p[0]},${p[1]}`).join(" ");

const interchangeNames = new Set(["Snowdon","Lionel-Groulx","Berri-UQAM","Jean-Talon"]);
const uniqueStations = new Map();
for (const [key,line] of Object.entries(lines)) {
  line.names.forEach((name,i)=>{
    if(!uniqueStations.has(name)) uniqueStations.set(name,{name,p:line.points[i],lines:[key]});
    else uniqueStations.get(name).lines.push(key);
  });
}

function labelFor(st, idx) {
  const [x,y]=st.p;
  const side = idx%2===0 ? 1 : -1;
  let dx=9, dy=side*8, anchor="start";
  if(x>330){dx=-9;anchor="end";}
  if(st.name==="Berri-UQAM"){dx=13;dy=-11;anchor="start";}
  if(st.name==="Lionel-Groulx"){dx=-13;dy=13;anchor="end";}
  if(st.name==="Snowdon"){dx=-13;dy=11;anchor="end";}
  if(st.name==="Jean-Talon"){dx=13;dy=-10;anchor="start";}
  return `<text x="${fmt(x+dx)}" y="${fmt(y+dy)}" text-anchor="${anchor}">${esc(st.name)}</text>`;
}

let lineSvg="";
for (const [key,line] of Object.entries(lines)) {
  lineSvg += `<g id="ligne-${key}" inkscape:groupmode="layer" inkscape:label="Ligne ${key}">\n`;
  for(const route of line.routes) lineSvg += `<polyline points="${polyPoints(route)}" fill="none" stroke="${line.color}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>\n`;
  lineSvg += `</g>\n`;
}

let pointsSvg=`<g id="stations" inkscape:groupmode="layer" inkscape:label="Stations DEL 12 mm">\n`;
let labelsSvg=`<g id="noms" inkscape:groupmode="layer" inkscape:label="Noms des stations">\n`;
let drillSvg="";
let idx=0;
for(const st of uniqueStations.values()){
  const [x,y]=st.p;
  const ring = interchangeNames.has(st.name) ? 1.4 : 0.65;
  pointsSvg += `<circle cx="${fmt(x)}" cy="${fmt(y)}" r="6" fill="#252728" stroke="#F2F0E9" stroke-width="${ring}"/>\n`;
  labelsSvg += labelFor(st,idx++)+"\n";
  drillSvg += `<g><circle cx="${fmt(x)}" cy="${fmt(y)}" r="6" fill="none" stroke="#000" stroke-width="0.25"/><path d="M ${fmt(x-2)} ${fmt(y)} H ${fmt(x+2)} M ${fmt(x)} ${fmt(y-2)} V ${fmt(y+2)}" stroke="#000" stroke-width="0.2"/></g>\n`;
}
pointsSvg += `</g>\n`;
labelsSvg += `</g>\n`;

const svg = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="18in" height="24in" viewBox="0 0 ${W} ${H}">
<rect width="${W}" height="${H}" fill="#252728"/>
<g inkscape:groupmode="layer" inkscape:label="Titre"><text x="34" y="42" fill="#F2F0E9" font-family="Arial, Helvetica, sans-serif" font-size="12" font-weight="700">Métro</text><text x="34" y="55" fill="#F2F0E9" font-family="Arial, Helvetica, sans-serif" font-size="12" font-weight="700">Montréal</text></g>
${lineSvg}${pointsSvg}${labelsSvg}
<style>text{fill:#F2F0E9;font-family:Arial,Helvetica,sans-serif;font-size:3.1px;font-weight:400;paint-order:stroke;stroke:#252728;stroke-width:1.4px;stroke-linejoin:round}</style>
</svg>`;

const drill = `<svg xmlns="http://www.w3.org/2000/svg" width="18in" height="24in" viewBox="0 0 ${W} ${H}">
<rect width="${W}" height="${H}" fill="#fff"/>
<g>${drillSvg}</g>
<path d="M 20 580 H 120" stroke="#000" stroke-width="0.5"/>
<text x="20" y="575" font-family="Arial" font-size="4">BARRE DE CONTRÔLE 100 mm — IMPRIMER À 100 %</text>
</svg>`;

fs.writeFileSync(OUT,svg);
fs.writeFileSync(DRILL,drill);
console.log(`${OUT}\n${DRILL}\n${uniqueStations.size} stations uniques`);
