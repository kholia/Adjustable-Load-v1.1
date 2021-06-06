#!/usr/bin/python2
#
# This python script convert legacy *.mod file to .pretty library format
#
# python convertModToPretty [MOD_DIR]
#
# https://github.com/nhatkhai/kicad_scripts/tree/master/convertors
import os
import glob
import pprint
import sys


def main():
  mod_dir = ''
  if len(sys.argv)==2:
    mod_dir = sys.argv[1]
  elif len(sys.argv)==1:
    s = raw_input("Please enter MOD DIR [" + mod_dir + "] ")
    if s: mod_dir = s

  for mod_file in glob.glob(os.path.join(mod_dir, "*.mod")):
    print "****************************************************"
    print "***** Process file ", mod_file
    print "****************************************************"
    pretty_dir = os.path.join(
      os.path.dirname(mod_file)
      , os.path.basename(mod_file) + ".pretty")
    convertModToPretty(mod_file, pretty_dir)
    print "Result can be find in ", pretty_dir


mod_Unit = 2.54e-3 # Assume default in is in 0.1mil/count

layerDic = {
    0  : 'B.Cu',
    15 : 'F.Cu',
    16 : 'B.Adhes',
    17 : 'F.Adhes',
    18 : 'B.Paste',
    19 : 'F.Paste',
    20 : 'B.SilkS',
    21 : 'F.SilkS',
    22 : 'B.Mask',
    23 : 'F.Mask',
    24 : 'Dwgs.User',
    25 : 'Cmts.User',
    26 : 'Eco1.User',
    27 : 'Eco2.User',
    28 : 'Edge.Cuts',
}

def getLayers(bitMask, testMask=0xFFFFFFFF):
    layers = []
    i = 0
    bitMask = long(bitMask, 16) & testMask
    while bitMask!=0:
        if (bitMask & 0x1)!=0:
            if i in layerDic:
                layers.append(layerDic[i])
        bitMask = bitMask >> 1
        i = i + 1
    return ' '.join(layers)

def genAT(x,y,a):
    angle = int(a)/10.0
    if (angle==0): return "{0} {1}".format(genNum(x),genNum(y))
    else         : return "{0} {1} {2:g}".format(genNum(x),genNum(y),angle)

def genOfs(ofsx, ofsy):
    if float(ofsx)==0 and float(ofsy)==0:
        return ''
    else:
        return ' (offset {0} {1})'.format(genNum(ofsx), genNum(ofsy))

def genText(txt):
    if txt.find(' ')>=0 \
    or txt.find('(')>=0 \
    or txt.find(')')>=0:
        return '"' + txt +'"'
    else:
        return txt

def genNum(text):
    return '{0:.6g}'.format(float(text)*mod_Unit)

def convertModToPretty(mod_file, pretty_dir):
    #
    # Reference http://www.compuphase.com/electronics/LibraryFileFormats.pdf
    # Reference https://en.wikibooks.org/wiki/Kicad/file_formats
    #
    lineCnt = 0
    curDIC = {' dics':[]}
    curARR = curDIC[' dics']

    if not os.path.exists(pretty_dir):
        os.makedirs(pretty_dir)

    global mod_Unit
    global layerDic

    mod_Unit = 2.54e-3 # Assume default in is in 0.1mil/count

    pp = pprint.PrettyPrinter(indent=4)
    mod_fileName = os.path.basename(mod_file)
    for line in open(mod_file):
        # Process a line
        lineCnt = lineCnt + 1
        items = line.replace('\n','').split(' ')

        # Generate pretty file here
        if items[0].startswith('$EndMODULE'):

            unit = curDIC[' prev'].setdefault('Units',[''])[0]
            if unit:
                if unit.lower()=='mm':
                    mod_Unit = 1.0
                else:
                    pp.pprint(['Unrecognized unit of ', unit])
                pp.pprint(["Mod file unit ",unit])

            cur = curDIC
            modName = ' '.join(cur['$MODULE'])

            #Po X Y A Layer Tedit Tstamp Attr
            #Cd description
            #Kw keywords
            #At Type
            tedit = cur.setdefault('Po',['','','','','0','0','~~'])[4]
            locked= 'locked ' if cur['Po'][6][0]=='F' else ''
            placed= 'placed ' if cur['Po'][6][1]=='P' else ''
            layer = layerDic[int(cur['Po'][3])]
            descr = genText(' '.join(cur.setdefault('Cd',[])))
            tags  = genText(' '.join(cur.setdefault('Kw',[''])))
            attr  = cur.setdefault('At',[''])[0].lower()
            yMax = 0

            pp.pprint("*** Processing [{line:5}] on {mod} ***".format(mod=modName,line=lineCnt))

            prettyfile = os.path.join(pretty_dir, modName + '.kicad_mod')
            fout = open( prettyfile, 'w+' )
            fout.write('(module {mod} {locked}{placed}(layer {layer}) (tedit {tedit})\n' \
                .format(
                    mod   = genText(modName),
                    tedit = tedit,
                    layer = layer,
                    locked= locked,
                    placed= placed,
                  ) )
            if descr: fout.write('  (descr {0})\n'.format(descr))
            if tags : fout.write('  (tags {0})\n'.format(tags))
            if attr : fout.write('  (attr {0})\n'.format(attr))

            #Process all T* X Y H W A Pen Mirror Visible Layer Italic "Text"
            for txt in cur.setdefault('T',[]):
                lbl = txt[11][1:-1]
                if   txt[0]=='T0':
                    type = 'reference'
                    if not lbl: lbl = 'Ref**'
                elif txt[0]=='T1':
                    type = 'value'
                    if not lbl: lbl = 'Val**'
                elif txt[0]=='T2':
                    type = 'user'
                else:
                    pp.pprint(["Unrecognized ",txt])
                    continue

                fout.write('  (fp_text {type} {lbl} (at {at}) (layer {layer}){visible}\n' \
                           '    (effects (font (size {W} {H}) (thickness {Pen})))\n'\
                           '  )\n' \
                  .format(
                    lbl     = genText(lbl),
                    at      = genAT(txt[1], txt[2], txt[5]),
                    layer   = layerDic[int(txt[9])],
                    visible = ' hide' if txt[8]=='I' else '',
                    type    = type,
                    W       = genNum(txt[3]),
                    H       = genNum(txt[4]),
                    Pen     = genNum(txt[6]), ))
                y = float(txt[2])
                if y>yMax: yMax = y

            # Process all D*
            DpCount = 0
            DpPen = ''
            DpLayer = ''
            for d in cur.setdefault('D',[]):

                # Process all DS X1 Y1 X2 Y2 Pen Layer
                if d[0]=='DS':
                    fout.write('  (fp_line (start {x1} {y1}) (end {x2} {y2}) (layer {layer}) (width {pen}))\n' \
                      .format( x1   =genNum(d[1]),
                               y1   =genNum(d[2]),
                               x2   =genNum(d[3]),
                               y2   =genNum(d[4]),
                               layer=layerDic[int(d[6])],
                               pen  =genNum(d[5]),
                             ))

                # Process all DC X Y Xp Yp Pen Layer
                elif d[0]=='DC':
                    fout.write('  (fp_circle (center {x} {y}) (end {xp} {yp}) (layer {layer}) (width {pen}))\n'\
                      .format( x    =genNum(d[1]),
                               y    =genNum(d[2]),
                               xp   =genNum(d[3]),
                               yp   =genNum(d[4]),
                               layer=layerDic[int(d[6])],
                               pen  =genNum(d[5]),
                             ))

                # Process all DA X Y Xp Yp Angle Pen Layer
                elif d[0]=='DA':
                    fout.write('  (fp_arc (start {x} {y}) (end {xp} {yp}) (angle {a}) '\
                               '(layer {layer}) (width {pen}))\n'\
                      .format( x    = genNum(d[1]),
                               y    = genNum(d[2]),
                               xp   = genNum(d[3]),
                               yp   = genNum(d[4]),
                               a    = d[5],
                               layer= layerDic[int(d[7])],
                               pen  = genNum(d[6]),
                             ))


                # Process all DP 0 0 0 0 Count Pen Layer
                # Process all Dl X Y
                elif d[0]=='DP':
                    DpCount = int(d[5])
                    DpPen   = genNum(d[6])
                    DpLayer = layerDic[int(d[7])]
                    fout.write('  (fp_poly (pts')
                elif d[0]=='Dl':
                    DpCount = DpCount - 1
                    if DpCount>=0:
                        fout.write(' (xy {x} {y})' \
                            .format(
                                x = genNum(d[1]),
                                y = genNum(d[2]),
                            ))
                        if DpCount % 4==3: fout.write('\n   ')
                    else:
                        pp.pprint("Got too many Dl")

                    if DpCount==0:
                        fout.write(')\n'
                                   '    (layer {layer}) (width {pen})\n ' \
                                   '  )\n' \
                                .format(
                                    layer = DpLayer,
                                    pen   = DpPen,
                                ))
                else:
                    pp.pprint(["Unrecognized ", d])

                y = float(d[2])
                if y>yMax: yMax = y
                if len(d)>4:
                    y = float(d[4])
                    if y>yMax: yMax = y

            for dic in cur.setdefault(' dics',[]):
                #Process all PADs
                if dic[' name']=='$PAD':
                    # Po X Y
                    # Sh "Name" Shape W H Ydelta Xdelta Orientation
                    # At Type N Mask
                    # Dr Size X Y
                    # Dr Size X Y O W H

                    At = dic.setdefault('At', ['','','0'])
                    if At[0].lower()=='std':
                        kind = 'thru_hole'
                        layers = ' (layers *.Cu {0})'.format(getLayers(dic['At'][2],0xFFFF0000))
                    elif At[0].lower()=='smd':
                        kind   = 'smd'
                        layers = ' (layers {0})'.format(getLayers(dic['At'][2]))
                    #TODO elif At[0].lower()=='con':
                    #TODO elif At[0].lower()=='hole':
                    else:
                        kind   = ''
                        layers = ''
                        pp.pprint(["Unrecognized ", At])

                    if dic['Sh'][1]=='R':
                        shape = 'rect (at {at}) (size {W} {H})' \
                            .format(
                                at = genAT(dic['Po'][0], dic['Po'][1], dic['Sh'][6]),
                                W  = genNum(dic['Sh'][2]),
                                H  = genNum(dic['Sh'][3]),
                                )
                    elif dic['Sh'][1]=='C':
                        shape = 'circle (at {x} {y}) (size {W} {H})'\
                            .format(
                                x = genNum(dic['Po'][0]),
                                y = genNum(dic['Po'][1]),
                                W = genNum(dic['Sh'][2]),
                                H = genNum(dic['Sh'][3]),
                                )
                    elif dic['Sh'][1]=='O':
                        shape ='oval (at {at}) (size {W} {H})'\
                            .format(
                                at= genAT(dic['Po'][0], dic['Po'][1], dic['Sh'][6]),
                                W = genNum(dic['Sh'][2]),
                                H = genNum(dic['Sh'][3]),
                                )
                    #TODO elif dic['Sh'][1]=='T':
                    else:
                        pp.pprint(["Unrecognized Sh ", dic['Sh']])
                        shape=''

                    #Drill information
                    #DR SIZE X Y
                    #DR SIZE X Y O W H
                    drill = []
                    for d in dic.setdefault('D',[]):
                        if d[0]=='Dr':
                            if float(d[1])!=0:
                                if len(d)==4:
                                    drill.append('(drill {sz}{ofs})'.format(
                                            sz = genNum(d[1]), ofs = genOfs(d[2], d[3]),
                                        ))
                                elif len(d)==7 and d[4]=='O':
                                    drill.append('(drill oval {w} {h} {ofs})'.format(
                                            sz = genNum(d[1]), ofs = genOfs(d[2], d[3]),
                                            w  = genNum(d[5]), h   = genNum(d[6]),
                                        ))
                                else:
                                    pp.pprint(['Unrecognized ',d])
                        else:
                            pp.pprint(['Unrecognized ',d])
                    if drill: drill = ' ' + ' '.join(drill)
                    else:     drill = ''

                    fout.write('  (pad {name} {kind} {shape}{drill}{layers}'\
                        .format(
                            name    = genText(dic['Sh'][0][1:-1]),
                            kind    = kind,
                            shape   = shape,
                            drill   = drill,
                            layers  = layers,
                                ))

                    y = float(dic['Po'][1])
                    if y>yMax: yMax = y

                    fout.write(')\n')

                #Process all SHAPE3D Models
                elif dic[' name']=='$SHAPE3D':
                    fout.write('  (model {model}\n' \
                               '    (at (xyz {Ofsx} {Ofsy} {Ofsz}))\n' \
                               '    (scale (xyz {Sc}))\n' \
                               '    (rotate (xyz {Ro}))\n' \
                               '  )\n' \
                        .format(model= genText(dic['Na'][0][1:-1]),
                                Ofsx = genNum(dic['Of'][0]),
                                Ofsy = genNum(dic['Of'][1]),
                                Ofsz = genNum(dic['Of'][2]),
                                Sc   = ' '.join(dic['Sc']),
                                Ro   = ' '.join(dic['Ro']) ))

            fout.write('  (fp_text user "{0}[{1}]" (at 0 {2:g}) (layer Cmts.User) hide\n' \
                       '    (effects (font (size 0.4 0.4) (thickness 0.1)))\n' \
                       '  )\n' \
                .format(mod_fileName, lineCnt, yMax*mod_Unit+1.0))

            fout.write(')')
            fout.close()

            curDIC = {' dics':[]}
            curARR = curDIC[' dics']

        # Go back to parent structure
        elif items[0].startswith('$End'):
            if ' prev' in curDIC:
                curDIC = curDIC[' prev']
                curARR = curDIC[' dics']
            continue

        # Generate child structure
        elif items[0].startswith('$'):
            curDIC = {' name':items[0],
                      ' prev':curDIC,
                      ' dics':[] }
            curARR.append(curDIC)
            curARR = curDIC[' dics']

        # Buildup data structure
        if items[0].startswith('T'):
            array = curDIC.setdefault('T',[])
            array.append(items)
        elif items[0].startswith('D'):
            array = curDIC.setdefault('D',[])
            array.append(items)
        else:
            curDIC[items[0]] = items[1:]

if __name__  == "__main__":
  main()
