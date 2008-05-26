"""
    MoinMoin - Python Source Parser
"""

# this comes from the Python Cookbook
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52298
# Cookboox recipes (printed ones anyway) are under the BSD license
# modifications by Roger Binns also BSD licensed
#  - the __name__=='__main__' section has been replaced
#  - pre tag is not generated
#  - if line contains <!-@!@-> then no entity escaping happens
#  - output can be captured and put inline into code
#  - some optimising of the html generated to reduce number of tags to minimum necessary
#  - using spans with css classes instead of font tags

# Imports
import cgi, string, sys, cStringIO
import keyword, token, tokenize


#############################################################################
### Python Source Parser (does Hilighting)
#############################################################################

_KEYWORD = token.NT_OFFSET + 1
_TEXT    = token.NT_OFFSET + 2

_styles = {
    token.NUMBER:       'pynumber',
    token.OP:           'pyoperator',
    token.STRING:       'pystring',
    tokenize.COMMENT:   'pycomment',
    token.NAME:         'pyname',
    token.ERRORTOKEN:   'pyerror',
    _KEYWORD:           'pykeyword',
    _TEXT:              'pytext',
}

# easier to do this than change all code ...
_colors=_styles

class Parser:
    """ Send colored python source.
    """

    def __init__(self, raw, out = sys.stdout, capturepattern="%d"):
        """ Store the source text.
        """
        self.raw = string.strip(string.expandtabs(raw))
        self.out = out
        self.capturecounter=0
        self.capturepattern=capturepattern
        self.prevcolour=None

    def format(self, formatter, form):
        """ Parse and send the colored source.
        """
        # store line offsets in self.lines
        self.lines = [0, 0]
        pos = 0
        while 1:
            pos = string.find(self.raw, '\n', pos) + 1
            if not pos: break
            self.lines.append(pos)
        self.lines.append(len(self.raw))

        # parse the source and write it
        self.pos = 0
        text = cStringIO.StringIO(self.raw)
        self.out.write('<font face="Lucida,Courier New,monospace">')
        try:
            tokenize.tokenize(text.readline, self)
        except tokenize.TokenError, ex:
            msg = ex[0]
            line = ex[1][0]
            self.out.write("<h3>ERROR: %s</h3>%s\n" % (
                msg, self.raw[self.lines[line]:]))
        # last item isn't closed
        self.out.write('</span>')
        # match font tag setting face above
        self.out.write('</font>')

    def __call__(self, toktype, toktext, (srow,scol), (erow,ecol), line):
        """ Token handler.
        """
        if 0:
            print "type", toktype, token.tok_name[toktype], "text", toktext,
            print "start", srow,scol, "end", erow,ecol, "<br>"

        # calculate new positions
        oldpos = self.pos
        newpos = self.lines[srow] + scol
        self.pos = newpos + len(toktext)

        # handle newlines
        if toktype in [token.NEWLINE, tokenize.NL]:
            self.out.write('\n')
            return

        # send the original whitespace, if needed
        if newpos > oldpos:
            self.out.write(self.raw[oldpos:newpos])

        # skip indenting tokens
        if toktype in [token.INDENT, token.DEDENT]:
            self.pos = newpos
            return

        # map token type to a color group
        if token.LPAR <= toktype and toktype <= token.OP:
            toktype = token.OP
        elif toktype == token.NAME and keyword.iskeyword(toktext):
            toktype = _KEYWORD
        color = _colors.get(toktype, _colors[_TEXT])

        style = ''
        if toktype == token.ERRORTOKEN:
            style = ' style="border: solid 1.5pt #FF0000;"'

        # capture?
        if toktext.startswith("#@@CAPTURE"):
            return # pretend line didn't exist
        elif toktext.startswith("#@@ENDCAPTURE"):
            fname=self.capturepattern % self.capturecounter
            self.capturecounter+=1
            # we put spaces in front of each line - using <blockquote> implies a new <p> and gives blank lines
            self.out.write('\n</span><span class="pyoutput">'+cgi.escape("".join(["   "+line for line in open(fname, "rt")]))+'</span>')
            self.prevcolour=None
            return

        # send text
        if len(toktext.strip())==0:
            # only whitespace so no need for colour!
            self.out.write(cgi.escape(toktext))
            return
        if self.prevcolour!=color:
            if self.prevcolour!='pytext' and self.prevcolour is not None:
                self.out.write('</span>')
            self.prevcolour=color
            if color!='pytext':
                self.out.write('<span class="%s"%s>' % (color, style))
                
        if "<!-@!@->" in toktext:  # line contains html - don't quote
            toktext=toktext.replace("<!-@!@->", "")
            self.out.write(toktext)
        else:
            self.out.write(cgi.escape(toktext))


def getcode(fname):
    # Returns the code between #@@BEGIN and #@@END markers
    code=[]
    op=False
    for line in open(fname, "rU"):
        line=line[:-1] # strip off newline
        if line.startswith("#@@BEGIN"):
            op=True
            continue
        if line.startswith("#@@END") and not line.startswith("#@@ENDCAPTURE"):
            op=False
            continue
        if op: code.append(line)
    return "\n".join(code)

def docapture(filename):
    code=[]
    code.append(outputredirector)
    counter=0
    for line in open(filename, "rU"):
        line=line[:-1] # strip off newline
        if line.startswith("#@@CAPTURE"):
            code.append("opto('.tmpop-%s-%d')" % (filename, counter))
            counter+=1
        elif line.startswith("#@@ENDCAPTURE"):
            code.append("opnormal()")
        else:
            code.append(line)
    code="\n".join(code)
    open("xx.py", "wt").write(code)
    exec code in {}

outputredirector="""
import sys
origsysstdout=None
def opto(fname):
  global origsysstdout
  origsysstdout=sys.stdout,fname
  sys.stdout=open(fname, "wt")
def opnormal():
  sys.stdout.close()
  sys.stdout=origsysstdout[0]
  sys.stdout.write(open(origsysstdout[1], "rb").read())
"""

if __name__ == "__main__":
    import os, sys, StringIO
    print "Formatting..."

    incode=False
    htmlout=[]
    for line in open("apsw.html", "rU"):
        line=line[:-1] # strip off newline
        if "<!--sourcestart-->" in line:
            incode=True
            htmlout.append(line)
            continue
        elif "<!--sourceend-->" in line:
            incode=False
            docapture("example-code.py")
            code=getcode("example-code.py")
            ostr=StringIO.StringIO()
            Parser(code, ostr, capturepattern='.tmpop-example-code.py-%d').format(None, None)
            htmlout.append(ostr.getvalue())
            htmlout.append(line)
            continue
        if not incode:
            htmlout.append(line)

    open("apsw.html", "wt").write("\n".join(htmlout))

