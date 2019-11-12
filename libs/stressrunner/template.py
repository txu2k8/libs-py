# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

#  ____  _                       ____
# / ___|| |_ _ __ ___  ___ ___  |  _ \ _   _ _ __  _ __   ___ _ __
# \___ \| __| '__/ _ \/ __/ __| | |_) | | | | '_ \| '_ \ / _ \ '__|
#  ___) | |_| | |  __/\__ \__ \ |  _ <| |_| | | | | | | |  __/ |
# |____/ \__|_|  \___||___/___/ |_| \_\\__,_|_| |_|_| |_|\___|_|

"""Define a HTML template for report customerization and generation.

    Overall structure of an HTML report

        HTML
        +------------------------+
        |<html>                  |
        |  <head>                |
        |                        |
        |   STYLESHEET           |
        |   +----------------+   |
        |   |                |   |
        |   +----------------+   |
        |                        |
        |  </head>               |
        |                        |
        |  <body>                |
        |                        |
        |   HEADING              |
        |   +----------------+   |
        |   |                |   |
        |   +----------------+   |
        |                        |
        |   REPORT               |
        |   +----------------+   |
        |   |                |   |
        |   +----------------+   |
        |                        |
        |   ENDING               |
        |   +----------------+   |
        |   |                |   |
        |   +----------------+   |
        |                        |
        |  </body>               |
        |</html>                 |
        +------------------------+

    """

# -----------------------------
# --- STATUS
# -----------------------------
STATUS = {
        0: 'PASS',
        1: 'FAIL',
        2: 'ERROR',
        3: 'SKIP',
        4: 'PASS(Canceled By User)',
    }


# -----------------------------
# --- HTML Template
# --- variables: (title, heading, report)
# -----------------------------
HTML_TEMPLATE = r"""
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>
            %(title)s
        </title>
        <meta name="generator" content="StressRunner 1.0.0" />
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <link href="http://libs.baidu.com/bootstrap/3.0.3/css/bootstrap.min.css"
        rel="stylesheet">
        <script src="http://libs.baidu.com/jquery/2.0.0/jquery.min.js">
        </script>
        <script src="http://libs.baidu.com/bootstrap/3.0.3/js/bootstrap.min.js">
        </script>
        %(stylesheet)s
    </head>
    <body>
        <script language="javascript" type="text/javascript">
            output_list = Array();

            /*level
    0:Summary //all hiddenRow
    1:Pass    //pt none, ft/et/st hiddenRow
    2:Failed  //ft none, pt/et/st hiddenRow,
    3:Error   //et none, pt/ft/st hiddenRow
    4:Skiped  //st none, pt/ft/et hiddenRow
    5:All     //pt/ft/et/st none
    */
            function showCase(level) {
                trs = document.getElementsByTagName("tr");
                for (var i = 0; i < trs.length; i++) {
                    tr = trs[i];
                    id = tr.id;
                    if (id.substr(0, 2) == 'ft') {
                        if (level == 4 || level == 3 || level == 1 || level == 0) {
                            tr.className = 'hiddenRow';
                        } else {
                            tr.className = '';
                        }
                    }
                    if (id.substr(0, 2) == 'pt') {
                        if (level == 4 || level == 3 || level == 2 || level == 0) {
                            tr.className = 'hiddenRow';
                        } else {
                            tr.className = '';
                        }
                    }
                    if (id.substr(0, 2) == 'et') {
                        if (level == 4 || level == 2 || level == 1 || level == 0) {
                            tr.className = 'hiddenRow';
                        } else {
                            tr.className = '';
                        }
                    }
                    if (id.substr(0, 2) == 'st') {
                        if (level == 3 || level == 2 || level == 1 || level == 0) {
                            tr.className = 'hiddenRow';
                        } else {
                            tr.className = '';
                        }
                    }
                }

                //add detail_class
                detail_class = document.getElementsByClassName('detail');

                //console.log(detail_class.length)
                if (level == 5) {
                    for (var i = 0; i < detail_class.length; i++) {
                        detail_class[i].innerHTML = "outline"
                    }
                } else {
                    for (var i = 0; i < detail_class.length; i++) {
                        detail_class[i].innerHTML = "detail"
                    }
                }
            }

            function showClassDetail(cid, count) {
                var id_list = Array(count);
                var toHide = 1;
                for (var i = 0; i < count; i++) {
                    tid0 = 't' + cid.substr(1) + '_' + (i + 1);
                    tid = 'f' + tid0;
                    tr = document.getElementById(tid);
                    if (!tr) {
                        tid = 'p' + tid0;
                        tr = document.getElementById(tid);
                        if (!tr) {
                            tid = 'e' + tid0;
                            tr = document.getElementById(tid);
                            if (!tr) {
                                tid = 's' + tid0;
                                tr = document.getElementById(tid);
                            }
                        }
                    }
                    id_list[i] = tid;
                    if (tr.className) {
                        toHide = 0;
                    }
                }
                for (var i = 0; i < count; i++) {
                    tid = id_list[i];
                    if (toHide) {
                        document.getElementById(tid).className = 'hiddenRow';
                        document.getElementById(cid).innerText = "detail"
                    } else {
                        document.getElementById(tid).className = '';
                        document.getElementById(cid).innerText = "outline"
                    }
                }
            }

            function html_escape(s) {
                s = s.replace(/&/g, '&amp;');
                s = s.replace(/</g, '&lt;');
                s = s.replace(/>/g, '&gt;');
                return s;
            }

            function drawCircle(pass, fail, error, skip) {
                var color = ["#6c6", "#c00", "#c60", "#d7d808"];
                var data = [pass, fail, error, skip];
                var text_arr = ["pass", "fail", "error", "skip"];

                var canvas = document.getElementById("circle");
                var ctx = canvas.getContext("2d");
                var startPoint = 0;
                var width = 28,
                height = 14;
                var posX = 112 * 2 + 20,
                posY = 30;
                var textX = posX + width + 5,
                textY = posY + 10;
                for (var i = 0; i < data.length; i++) {
                    ctx.fillStyle = color[i];
                    ctx.beginPath();
                    ctx.moveTo(112, 70);
                    ctx.arc(112, 70, 70, startPoint, startPoint + Math.PI * 2 * (data[i] / (data[0] + data[1] + data[2])), false);
                    ctx.fill();
                    startPoint += Math.PI * 2 * (data[i] / (data[0] + data[1] + data[2]));
                    ctx.fillStyle = color[i];
                    ctx.fillRect(posX, posY + 20 * i, width, height);
                    ctx.moveTo(posX, posY + 20 * i);
                    ctx.font = 'bold 14px';
                    ctx.fillStyle = color[i];
                    var percent = text_arr[i] + " " + data[i];
                    ctx.fillText(percent, textX, textY + 20 * i);

                }
            }
        </script>
        <div class="piechart">
            <div>
                <canvas id="circle" width="350" height="168" </canvas>
            </div>
        </div>
        %(heading)s %(report)s
    </body>

</html>
"""


STYLESHEET_TEMPLATE = """
<style type="text/css" media="screen">
body        { font-family: Microsoft YaHei,Tahoma,arial,helvetica,sans-serif;padding: 20px; font-size: 80%; }
table       { font-size: 100%; }

/* -- heading ---------------------------------------------------------------------- */
h1 {
font-size: 16pt;
color: gray;
}
.heading {
margin-top: 0ex;
margin-bottom: 1ex;
}
.heading .attribute {
margin-top: 1ex;
margin-bottom: 0;
}
.heading .description {
margin-top: 4ex;
margin-bottom: 6ex;
}

/* -- report ------------------------------------------------------------------------ */
#total_row  { font-weight: bold; }
.passCase   { color: #5cb85c; }
.failCase   { color: #d9534f; font-weight: bold; }
.errorCase  { color: #f04e4e; font-weight: bold; }
.skipCase   { color: #f0a20d; font-weight: bold; }
.hiddenRow  { display: none; }
.testcase   { margin-left: 2em; }
.piechart{
position:absolute;  ;
top:75px;
left:400px;
width: 200px;
float: left;
display:  inline;
}
</style>
"""

# -----------------------------
# --- Heading Template
# --- variables: (title, parameters, description)
# -----------------------------
HEADING_TEMPLATE = """
<div class='heading'>
    <h1>
        %(title)s
    </h1>
    %(parameters)s
    <p class='description'>
        %(description)s
    </p>
</div>
"""

# -----------------------------
# --- Heading attribute
# --- variables: (name, value)
# -----------------------------
HEADING_ATTRIBUTE_TEMPLATE = """<p class='attribute'><strong>%(name)s:</strong>%(value)s</p>"""


# -----------------------------
# --- Report Template
# --- variables: (test_list, count, Pass, fail, error ,passrate)
# -----------------------------
REPORT_TEMPLATE = """
<p id='show_detail_line'>
<a class="btn btn-primary" href='javascript:showCase(0)'>Summary{ %(passrate)s }</a>
<a class="btn btn-success" href='javascript:showCase(1)'>Passed{ %(Pass)s }</a>
<a class="btn btn-danger" href='javascript:showCase(2)'>Failed{ %(fail)s }</a>
<a class="btn btn-danger" href='javascript:showCase(3)'>Error{ %(error)s }</a>
<a class="btn btn-warning" href='javascript:showCase(4)'>Skiped{ %(skip)s }</a>
<a class="btn btn-info" href='javascript:showCase(5)'>ALL{ %(count)s }</a>
</p>
<table id='result_table' class="table table-condensed table-bordered table-hover">
<colgroup>
<col align='left' />
<col align='right' />
<col align='right' />
<col align='right' />
<col align='right' />
<col align='right' />
</colgroup>
<tr id='header_row' class="text-center success" style="font-weight: bold;font-size: 14px;">
    <td>Test Group/Test case</td>
    <td>Count</td>
    <td>Pass</td>
    <td>Fail</td>
    <td>Error</td>
    <td>Skip</td>
    <td>View</td>
</tr>
%(test_list)s
<tr id='total_row' class="text-center active">
    <td>Total</td>
    <td>%(count)s</td>
    <td>%(Pass)s</td>
    <td>%(fail)s</td>
    <td>%(error)s</td>
    <td>%(skip)s</td>
    <td>Passing rate: %(passrate)s</td>
</tr>
</table>
<script>
    showCase(5);
    drawCircle(%(Pass)s, %(fail)s, %(error)s, %(skip)s);
</script>
"""


# -----------------------------
# --- Report class Template
# --- variables: (style, desc, count, Pass, fail, error, cid)
# -----------------------------
REPORT_CLASS_TEMPLATE = r"""
<tr class='%(style)s warning'>
    <td>%(desc)s</td>
    <td class="text-center">%(count)s</td>
    <td class="text-center">%(Pass)s</td>
    <td class="text-center">%(fail)s</td>
    <td class="text-center">%(error)s</td>
    <td class="text-center">%(skip)s</td>
    <td class="text-center"><a href="javascript:showClassDetail('%(cid)s',%(count)s)" class="detail" id='%(cid)s'>Detail</a></td>
</tr>
"""

REPORT_OUTPUT_TEMPLATE = r"""%(output)s"""  # variables: (id, output)

REPORT_WITH_OUTPUT_TEMPLATE = r"""
    <tr id='%(tid)s' class='%(Class)s'>
        <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
        <td colspan='4' align='center'>
        <!--pack up error info default
        <button id='btn_%(tid)s' type="button"  class="btn btn-success btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
        <div id='div_%(tid)s' class="collapse">  -->

        <!-- unfold error info default -->
        <button id='btn_%(tid)s' type="button"  class="btn btn-success btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
        <div align='left'>
        <div id='div_%(tid)s' class="collapse"><pre>%(script)s</pre></div>
        <!--css div popup end-->

        <td colspan='1' align='center'>%(elapsedtime)s</td>
        <td colspan='1' align='center'>Loop: %(iteration)s</td>
        </td>
    </tr>
    """  # variables: (tid, Class, style, desc, status)

REPORT_NO_OUTPUT_TEMPLATE = r"""
<tr id='%(tid)s' class='%(Class)s'>
    <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
    <td colspan='4' align='center'>
    <button id='btn_%(tid)s' type="button" class="btn btn-success btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
    <!--css div popup end-->

    <td colspan='1' align='center'>%(elapsedtime)s</td>
    <td colspan='1' align='center'>Loop: %(iteration)s</td>
</tr>
"""  # variables: (tid, Class, style, desc, status)

REPORT_WITH_ERROR_TEMPLATE = r"""
<tr id='%(tid)s' class='%(Class)s'>
    <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
    <td colspan='4' align='center'>
    <!--pack up error info default
    <button id='btn_%(tid)s' type="button"  class="btn btn-danger btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
    <div id='div_%(tid)s' class="collapse">  -->

    <!-- unfold error info default -->
    <button id='btn_%(tid)s' type="button"  class="btn btn-danger btn-xs" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
    <div align='left'>
    <div id='div_%(tid)s' class="collapse in"><pre>%(script)s</pre></div>
    <!--css div popup end-->

    <td colspan='1' align='center'>%(elapsedtime)s</td>
    <td colspan='1' align='center'>Loop: %(iteration)s</td>
    </td>
</tr>
"""  # variables: (tid, Class, style, desc, status)

REPORT_SKIP_TEMPLATE = r"""
    <tr id='%(tid)s' class='%(Class)s'>
        <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
        <td colspan='4' align='center'>
        <!--pack up error info default
        <button id='btn_%(tid)s' type="button"  class="btn btn-danger btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
        <div id='div_%(tid)s' class="collapse">  -->

        <!-- unfold error info default -->
        <button id='btn_%(tid)s' type="button"  class="btn btn-warning btn-xs" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
        <div align='left'>
        <div id='div_%(tid)s' class="collapse in"><pre>%(script)s</pre></div>
        <!--css div popup end-->

        <td colspan='1' align='center'>%(elapsedtime)s</td>
        <td colspan='1' align='center'>Loop: %(iteration)s</td>
        </td>
    </tr>
    """  # variables: (tid, Class, style, desc, status)
