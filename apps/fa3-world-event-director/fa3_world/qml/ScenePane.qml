import QtQuick
import QtQuick.Controls

Rectangle {
    id: scene
    required property string scope
    required property string heading
    required property string effects
    required property real rain
    required property real wind
    required property real clouds
    color: "#213b52"
    border.color: "#37566b"
    border.width: 1
    radius: 8
    clip: true

    Rectangle { x:1; y:1; width:parent.width-2; height:35; color:"#15283a"; radius:7 }
    Text { x:13; y:10; text: scene.heading; color:"#d9eaf3"; font.bold:true; font.pixelSize:13 }
    Canvas {
        id: art
        x:3; y:37; width:parent.width-6; height:parent.height-68
        onPaint: {
            let ctx = getContext('2d'); let w=width,h=height;
            ctx.clearRect(0,0,w,h);
            ctx.fillStyle = scene.clouds>50 ? '#35516b':'#6590b1'; ctx.fillRect(0,0,w,h);
            ctx.fillStyle = '#ffe0a0'; ctx.beginPath();ctx.arc(w*.78,24,17,0,6.3);ctx.fill();
            if(scene.scope==='NATURAL') {
                ctx.fillStyle='#537b73';ctx.beginPath();ctx.moveTo(0,h*.8);ctx.lineTo(w*.23,h*.26);ctx.lineTo(w*.48,h*.8);ctx.fill();
                ctx.fillStyle='#376d69';ctx.beginPath();ctx.moveTo(w*.25,h*.8);ctx.lineTo(w*.68,h*.16);ctx.lineTo(w,h*.8);ctx.fill();
                ctx.fillStyle='#346757';ctx.fillRect(0,h*.78,w,h*.22);
                for(let i=0;i<7;i++){let x=24+i*w/7;ctx.fillStyle='#70583c';ctx.fillRect(x,h*.67,4,h*.24);ctx.fillStyle='#3d8667';ctx.beginPath();ctx.moveTo(x-13,h*.76);ctx.lineTo(x+2,h*.43);ctx.lineTo(x+17,h*.76);ctx.fill();}
            } else if(scene.scope==='CITY'){
                ctx.fillStyle='#596e7b';ctx.fillRect(0,h*.75,w,h*.25);
                for(let i=0;i<7;i++){let x=10+i*w/7,bh=55+(i%3)*14;ctx.fillStyle=['#a39c90','#898f99','#a7897a'][i%3];ctx.fillRect(x,h*.75-bh,w/9,bh);
                ctx.fillStyle='#d6c6a6';for(let yy=0;yy<3;yy++)for(let xx=0;xx<2;xx++)ctx.fillRect(x+6+xx*16,h*.75-bh+12+yy*17,9,11);}
                ctx.fillStyle='#839fb1';if(scene.rain>1)for(let i=0;i<3;i++){ctx.beginPath();ctx.ellipse(w*.25+i*w*.25,h*.86,20,4,0,0,6.3);ctx.fill();}
            } else if(scene.scope==='BUILDING') {
                ctx.fillStyle='#456b58';ctx.fillRect(0,h*.83,w,h*.17);
                ctx.fillStyle='#b7aaa0';ctx.fillRect(w*.29,h*.37,w*.43,h*.48);
                ctx.fillStyle='#956e62';ctx.beginPath();ctx.moveTo(w*.25,h*.4);ctx.lineTo(w*.505,h*.08);ctx.lineTo(w*.76,h*.4);ctx.fill();
                ctx.fillStyle='#82b7ca';ctx.fillRect(w*.34,h*.53,w*.11,h*.22);ctx.fillRect(w*.56,h*.53,w*.11,h*.22);
                ctx.strokeStyle='#b4dcec';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(w*.73,h*.37);ctx.lineTo(w*.73,h*.91);ctx.stroke();
            } else {
                ctx.fillStyle='#7f8790';ctx.fillRect(0,0,w,h);
                ctx.fillStyle='#c6b8ac';ctx.fillRect(0,h*.84,w,h*.16);ctx.fillRect(w*.12,h*.13,w*.45,h*.65);
                ctx.fillStyle='#689cb6';ctx.fillRect(w*.16,h*.2,w*.37,h*.54);
                ctx.fillStyle='#ebedf2';ctx.fillRect(w*.33,h*.18,5,h*.58);
                if(scene.rain>=15 && scene.wind>=25){ctx.fillStyle='#7fd2f6';ctx.fillRect(w*.55,h*.48,5,h*.43);}
            }
            if(scene.clouds>20){for(let i=0;i<(scene.clouds>65?3:2);i++){let x=w*(.12+i*.25);ctx.fillStyle='#bbced8';
                for(let k=0;k<3;k++){ctx.beginPath();ctx.arc(x+k*14,21+6*(k%2),14,0,6.3);ctx.fill();}}}
            if(scene.rain>0 && scene.scope!=='INTERIOR') {
                ctx.strokeStyle='#a3defa';ctx.lineWidth=1;
                for(let i=0;i<Math.min(86,22+scene.rain*1.3);i++){let x=9+(i*73)%(Math.max(20,w-20)),y=50+(i*41)%(Math.max(20,h-60));ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-3-scene.wind/30,y+10);ctx.stroke();}}
        }
        Connections { target: world; function onRevisionChanged(){ art.requestPaint(); } }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }
    Rectangle { x:1; width:parent.width-2; height:30; anchors.bottom:parent.bottom; color:'#132639'; radius:5 }
    Text { x:13; anchors.bottom:parent.bottom; anchors.bottomMargin:9; width:parent.width-26; elide:Text.ElideRight; color:'#80dfbf'; font.pixelSize:11; text:scene.effects }
}
