
import wx
from wx import glcanvas
import os

import pyglet
pyglet.options['debug_gl'] = True
pyglet.options['shadow_window'] = False

import pyglet.canvas
from pyglet.gl import *

import numpy
import numpy.linalg

# When Subclassing wx.Window in Windows the focus goes to the wx.Window
# instead of GLCanvas and it does not draw the focus rectangle and
# does not consume used keystrokes
# BASE_CLASS = wx.Window
# Subclassing Panel solves problem In Windows
#BASE_CLASS = wx.Panel
# BASE_CLASS = wx.ScrolledWindow
BASE_CLASS = glcanvas.GLCanvas

class wxGLPanel(BASE_CLASS):
    '''A simple class for using OpenGL with wxPython.'''

    orbit_control = True
    orthographic = True
    color_background = (0.48, 0.28, 0.78, 1)
    do_lights = True

    def __init__(self, parent, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = 0,
                 antialias_samples = 0):
        # Full repaint should not be a performance problem
        style = style | wx.FULL_REPAINT_ON_RESIZE

        self.GLinitialized = False
        self.mview_initialized = False
        attribList = wx.glcanvas.GLAttributes()
        attribList.PlatformDefaults().MinRGBA(8, 8, 8, 8).DoubleBuffer().Depth(24)

        if antialias_samples > 0 and hasattr(glcanvas, "WX_GL_SAMPLE_BUFFERS"):
            attribList.SampleBuffers(1).Samplers(antialias_samples)

        attribList.EndList()

        if BASE_CLASS is glcanvas.GLCanvas:
            super().__init__(parent, attribList, wx.ID_ANY, pos, size, style)
            self.canvas = self
        else:
            super().__init__(parent, wx.ID_ANY, pos, size, style)
            self.canvas = glcanvas.GLCanvas(self, wx.ID_ANY, attribList, pos, size, style)

        self.width = self.height = None

        self.context = glcanvas.GLContext(self.canvas)

        #self.rot_lock = Lock()
        self.basequat = [0, 0, 0, 1]
        self.zoom_factor = 1.0
        self.angle_z = 0
        self.angle_x = 0

        self.gl_broken = False

        # bind events
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        if self.canvas is not self:
            self.Bind(wx.EVT_SIZE, self.OnScrollSize)
            # do not focus parent (panel like) but its canvas
            self.SetCanFocus(False)

        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        # In wxWidgets 3.0.x there is a clipping bug during resizing
        # which could be affected by painting the container
        # self.Bind(wx.EVT_PAINT, self.processPaintEvent)
        # Upgrade to wxPython 4.1 recommended
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)

        self.canvas.Bind(wx.EVT_SET_FOCUS, self.processFocus)
        self.canvas.Bind(wx.EVT_KILL_FOCUS, self.processKillFocus)

    def processFocus(self, ev):
        # print('processFocus')
        self.Refresh(False)
        ev.Skip()

    def processKillFocus(self, ev):
        # print('processKillFocus')
        self.Refresh(False)
        ev.Skip()
    # def processIdle(self, event):
    #     print('processIdle')
    #     event.Skip()

    def Layout(self):
        return super().Layout()

    def Refresh(self, eraseback=True):
        # print('Refresh')
        return super().Refresh(eraseback)

    def OnScrollSize(self, event):
        self.canvas.SetSize(event.Size)

    def processEraseBackgroundEvent(self, event):
        '''Process the erase background event.'''
        pass  # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event):
        '''Process the resize event.'''

        # print('processSizeEvent frozen', self.IsFrozen(), event.Size.x, self.ClientSize.x)
        if not self.IsFrozen() and self.canvas.IsShownOnScreen():
            # Make sure the frame is shown before calling SetCurrent.
            self.canvas.SetCurrent(self.context)
            self.OnReshape()

            # self.Refresh(False)
            # print('Refresh')
        event.Skip()

    def processPaintEvent(self, event):
        '''Process the drawing event.'''
        # print('wxGLPanel.processPaintEvent', self.ClientSize.Width)
        self.canvas.SetCurrent(self.context)

        if not self.gl_broken:
            try:
                self.OnInitGL()
                self.DrawCanvas()
            except pyglet.gl.lib.GLException:
                self.gl_broken = True
                print("OpenGL failed, disabling it:")
        event.Skip()

    def Destroy(self):
        # clean up the pyglet OpenGL context
        self.pygletcontext.destroy()
        # call the super method
        super().Destroy()

    # ==========================================================================
    # GLFrame OpenGL Event Handlers
    # ==========================================================================
    def OnInitGL(self, call_reshape = True):
        '''Initialize OpenGL for use in the window.'''
        if self.GLinitialized:
            return
        self.GLinitialized = True
        antialias_samples = 0

		#create your own context config:
        display = pyglet.canvas.get_display()
        screen = display.get_default_screen()
        if antialias_samples > 0: # and hasattr(glcanvas, "WX_GL_SAMPLE_BUFFERS"):
            template = pyglet.gl.Config(major_version=3, minor_version=3,
            					 sample_buffers=1, samples=antialias_samples,
								 depth_size=24, double_buffer=True)
        else:
             template = pyglet.gl.Config(major_version=3, minor_version=3,
								  depth_size=24, double_buffer=True) # forward_compatible = True, Core Profile

        try:
            config = screen.get_best_config(template)

        except pyglet.window.NoSuchConfigException:
            template = pyglet.gl.Config()
            config = screen.get_best_config(template)
        context = config.create_context(None)
        # create a pyglet context for this panel
        self.pygletcontext = pyglet.gl.Context(context)
        print('OpenGL version:', self.pygletcontext.canvas.get_info().get_version())
         # gl.Context is a pyglet function, current_context probably means that the context
         # is created by wxpython and reused by pyglet
        self.pygletcontext.canvas = self
        self.pygletcontext.set_current() # this is a pyglet function


        # normal gl init
        glClearColor(*self.color_background)
        glClearDepth(1.0)                # set depth value to 1
        glDepthFunc(GL_LEQUAL)
        #glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        if call_reshape:
            self.OnReshape()



    def DrawCanvas(self):
        """Draw the window."""
        #import time
        #start = time.perf_counter()
        # print('DrawCanvas', self.canvas.GetClientRect())
        self.pygletcontext.set_current()
        glClearColor(*self.color_background)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_objects()

        if self.canvas.HasFocus():
            self.drawFocus()
        self.canvas.SwapBuffers()
        #print('Draw took', '%.2f'%(time.perf_counter()-start))


class MyCanvasBase(glcanvas.GLCanvas):
    def __init__(self, parent):
        glcanvas.GLCanvas.__init__(self, parent, -1)
        self.init = False
        self.context = glcanvas.GLContext(self)

        # Initial mouse position.
        self.lastx = self.x = 30
        self.lasty = self.y = 30
        self.size = None
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)


    def OnEraseBackground(self, event):
        pass  # Do nothing, to avoid flashing on MSW.

    def OnSize(self, event):
        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def DoSetViewport(self):
        size = self.size = self.GetClientSize() * self.GetContentScaleFactor()
        self.SetCurrent(self.context)
        glViewport(0, 0, size.width, size.height)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.SetCurrent(self.context)
        if not self.init:
            self.InitGL()
            self.init = True
        self.OnDraw()

    def OnMouseDown(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        self.CaptureMouse()
        self.x, self.y = self.lastx, self.lasty = event.GetPosition()

    def OnMouseUp(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

    def OnMouseMotion(self, event):
        if event.Dragging() and event.LeftIsDown():
            self.lastx, self.lasty = self.x, self.y
            self.x, self.y = event.GetPosition()
            self.Refresh(False)


class CubeCanvas(MyCanvasBase):
    def InitGL(self):
        # Set viewing projection.
        #glMatrixMode(GL_PROJECTION)
        #glFrustum(-0.5, 0.5, -0.5, 0.5, 1.0, 3.0)

        # Position viewer.
        #glMatrixMode(GL_MODELVIEW)
        #glTranslatef(0.0, 0.0, -2.0)

        # Position object.
        #glRotatef(self.y, 1.0, 0.0, 0.0)
        #glRotatef(self.x, 0.0, 1.0, 0.0)

        glEnable(GL_DEPTH_TEST)
        #glEnable(GL_LIGHTING)
        #glEnable(GL_LIGHT0)

        self.textureID = None
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'bmp_source'))
        rd = 'pyglet.png'
        if os.path.exists(os.path.join(path, rd)):
            NotImplemented
            #self.textureID = GenerateTexture(*ReadTexture(os.path.join(path, rd)))


    def OnDraw(self):
        # Clear color and depth buffers.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Draw six faces of a cube.
        #glBegin(GL_QUADS)
        ## glNormal3f( 0.0, 0.0, 1.0)
        ## glVertex3f( 0.5, 0.5, 0.5)
        ## glVertex3f(-0.5, 0.5, 0.5)
        ## glVertex3f(-0.5,-0.5, 0.5)
        ## glVertex3f( 0.5,-0.5, 0.5)
        '''
        glNormal3f( 0.0, 0.0,-1.0)
        glVertex3f(-0.5,-0.5,-0.5)
        glVertex3f(-0.5, 0.5,-0.5)
        glVertex3f( 0.5, 0.5,-0.5)
        glVertex3f( 0.5,-0.5,-0.5)

        glNormal3f( 0.0, 1.0, 0.0)
        glVertex3f( 0.5, 0.5, 0.5)
        glVertex3f( 0.5, 0.5,-0.5)
        glVertex3f(-0.5, 0.5,-0.5)
        glVertex3f(-0.5, 0.5, 0.5)

        glNormal3f( 0.0,-1.0, 0.0)
        glVertex3f(-0.5,-0.5,-0.5)
        glVertex3f( 0.5,-0.5,-0.5)
        glVertex3f( 0.5,-0.5, 0.5)
        glVertex3f(-0.5,-0.5, 0.5)

        glNormal3f( 1.0, 0.0, 0.0)
        glVertex3f( 0.5, 0.5, 0.5)
        glVertex3f( 0.5,-0.5, 0.5)
        glVertex3f( 0.5,-0.5,-0.5)
        glVertex3f( 0.5, 0.5,-0.5)

        glNormal3f(-1.0, 0.0, 0.0)
        glVertex3f(-0.5,-0.5,-0.5)
        glVertex3f(-0.5,-0.5, 0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        glVertex3f(-0.5, 0.5,-0.5)
        glEnd()
        '''
        if self.textureID:
            glEnable(GL_TEXTURE_2D)
            ## glBindTexture(GL_TEXTURE_2D, self.textureID)

            '''            glBegin(GL_QUADS)
            glNormal3f( 0.0, 0.0, 1.0)
            glTexCoord2f(0.0, 0.0)
            glVertex3fv((0.5, 0.5, 0.5))
            glTexCoord2f(1.0, 0.0)
            glVertex3fv((-0.5, 0.5, 0.5))
            glTexCoord2f(1.0, 1.0)
            glVertex3fv((-0.5,-0.5, 0.5))
            glTexCoord2f(0.0, 1.0)
            glVertex3fv((0.5,-0.5, 0.5))
            glEnd()'''

        if self.size is None:
            self.size = self.GetClientSize()
        w, h = self.size
        w = max(w, 1.0)
        h = max(h, 1.0)
        xScale = 180.0 / w
        yScale = 180.0 / h
        #glRotatef((self.y - self.lasty) * yScale, 1.0, 0.0, 0.0);
        #glRotatef((self.x - self.lastx) * xScale, 0.0, 1.0, 0.0);

        self.SwapBuffers()


class OpenGLDemoWindow(wx.Frame):
    def __init__(self):
        super().__init__(parent=None,
        				  title='OpenGL WxPython pyglet Demo',
        				  size = (640, 480))

        #frame = wx.Frame(None, wx.ID_ANY, CubeCanvas, size=(400, 400))
        #canvas = MyCanvasBase(frame)
        #frame.Show(True)

        panel = wx.Panel(self)



        topsizer = wx.BoxSizer(wx.VERTICAL)
        c = CubeCanvas(panel)
        c.SetSize((200, 200))
        topsizer.Add(c, 0, wx.ALIGN_CENTER | wx.ALL, 15)
        #topsizer.Add(CubeCanvas(panel), wx.EXPAND)
        close_button = wx.Button(panel, wx.ID_CANCEL)
        topsizer.Add(close_button, 0, wx.ALL | wx.CENTER, 5)
        close_button.Bind(wx.EVT_BUTTON, self.on_close)

        panel.SetSizer(topsizer)
        self.Show()

    def on_close(self, event):
        """"""
        self.Close()

        #The wxPanel should be the only child of the wxFrame.
		#Then you add a wxSizer to the panel and put the wxGLCanvas (and probably other controls) into the sizer.
		#The wxGLCanvas and these controls must have the wxPanel as parent.
		#As the wxGLCanvas has no natural "best size" you need to set the sizer flags (wxEXPAND) and proportion parameter so that it consumes all available space.


if __name__ == '__main__':
    app = wx.App()
    frame = OpenGLDemoWindow()
    app.MainLoop()