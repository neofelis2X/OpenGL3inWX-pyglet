''' This example creates glcanvas with wxPython and hands
the graphic context over to pyglet. pyglet.gl is used to
draw a coloured triangle. It uses code from pyglet examples,
wxPython examples and amengede/getIntoGameDev pyOpengGL series'''

# Sources:
# GitHub: https://github.com/amengede/getIntoGameDev/blob/main/pyopengl/02%20-%20triangle/finished/triangle.py
# GitHub: https://github.com/tartley/gltutpy/blob/master/t01.hello-triangle/HelloTriangle.py#L76

import time
import wx
from wx import glcanvas
import pyglet
pyglet.options['debug_gl'] = True
pyglet.options['shadow_window'] = False
from pyglet.gl.gl import *
import ctypes
import numpy as np


def compile_shader(filepath: str, shader_type: type) -> int:
    '''Take a path to an opengl shader as string,
    prepare it with ctypes and compile a shader
        Parameters:
            shader_src: shader source code as string
        Returns:
            A handle to the compiled shader object
    '''
    with open(filepath,'r', encoding='utf-8') as f:
        shader_src = f.read()

    b_src = shader_src.encode('utf-8')
    src_len = ctypes.c_int(len(b_src))
    src_pointer = ctypes.cast(ctypes.c_char_p(b_src), ctypes.POINTER(ctypes.c_char))

    shader_id = glCreateShader(shader_type)
    glShaderSource(shader_id, 1, src_pointer, src_len)
    glCompileShader(shader_id)

    return shader_id

def create_shader_program(vertex_filepath: str, fragment_filepath: str) -> int:
    """
        Compile and link shader modules to make a shader program.
        Parameters:
            vertex_filepath: path to the text file storing the vertex
                             source code
            fragment_filepath: path to the text file storing the
                               fragment source code
        Returns:
            A handle to the created shader program
    """

    # Create and compile the shader objects
    vert_sh_id = compile_shader(vertex_filepath, GL_VERTEX_SHADER)
    frag_sh_id = compile_shader(fragment_filepath, GL_FRAGMENT_SHADER)

    # Link the shader in one program
    program_id = glCreateProgram()
    glAttachShader(program_id, vert_sh_id)
    glAttachShader(program_id, frag_sh_id)
    glLinkProgram(program_id)

    # Shader objects no longer needed
    glDetachShader(program_id, vert_sh_id)
    glDetachShader(program_id, frag_sh_id)

    return program_id


class Triangle:
    """
        Yep, it's a triangle.
    """
    def __init__(self):
        """
            Initialize a triangle.
        """
        # x, y, z, r, g, b
        vertices = (
            -0.5, -0.5, 0.0, 1.0, 0.3, 0.0,
             0.5, -0.5, 0.0, 0.7, 0.9, 0.0,
             0.0,  0.5, 0.0, 0.1, 0.3, 0.5
        )
        vertices = np.array(vertices, dtype=np.float32)
        # One way to convert the array to GLfloat
        array_type = GLfloat * len(vertices)
        vertices_gl = array_type(*vertices)

        self.vertex_count = 3

        # Vertex array object
        self.vao = GLuint(0)
        glGenVertexArrays(1, self.vao)
        glBindVertexArray(self.vao)
        # Vertex buffer object
        self.vbo = GLuint(0)
        glGenBuffers(1, self.vbo)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices_gl, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)  # Vertex position
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 24, 0)

        glEnableVertexAttribArray(1)  # Vertex colour
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 24, 12)

    def arm_for_drawing(self) -> None:
        """
            Arm the triangle for drawing.
        """
        glBindVertexArray(self.vao)

    def draw(self) -> None:
        """
            Draw the triangle. This is the actual drawcall
        """
        glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)

    def destroy(self) -> None:
        """
            Free any allocated memory.
        """
        glDeleteVertexArrays(1, self.vao)
        glDeleteBuffers(1, self.vbo)


class MyCanvasBase(glcanvas.GLCanvas):
    '''Create OpenGL canvas and context'''
    def __init__(self, parent, status_text: wx.StaticText):

        # Canvas attributes
        disp_attrs = wx.glcanvas.GLAttributes()
        # Set a 24bit depth buffer and activate double buffering for the canvas
        disp_attrs.PlatformDefaults().DoubleBuffer().Depth(24).EndList()
        glcanvas.GLCanvas.__init__(self, parent, disp_attrs, -1)

        # Context attributes
        # I'm not certain if this settings do anything here
        cxt_attrs = glcanvas.GLContextAttrs()
        cxt_attrs.PlatformDefaults().CoreProfile().MajorVersion(3).MinorVersion(3).EndList()
        self.wx_context = glcanvas.GLContext(self, ctxAttrs=cxt_attrs)
        # Feed the wx context to pyglet.
        # I'm surprised that this works, but somehow it does...
        self.pyg_context = pyglet.gl.Context(self.wx_context)
        # pyglet needs have a canvas so we define our new wx canvas
        self.pyg_context.canvas = self
        self.pyg_context.set_current()

        self.init = False
        self.parent = parent
        self.status_text = status_text

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
        self.SetCurrent(self.wx_context)
        glViewport(0, 0, size.width, size.height)

    def OnPaint(self, event):
        self.SetCurrent(self.wx_context)
        if not self.init:
            self.InitGL(self.status_text)
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


class Canvas(MyCanvasBase):
    '''Use OpenGL canvas'''
    def InitGL(self, status_text: wx.StaticText):
        '''Initialise ogl context'''
        self.fps_status = status_text
        self.last_time = 0
        self.sh_program = None
        self.triangle = None

        # Background colour
        COL_BG = (96, 147, 172)
        glClearColor(COL_BG[0] / 255, COL_BG[1] / 255, COL_BG[2] / 255, 1)

        # Enable depth testing and face culling. Not needed in this example
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)

        self._create_assets()


    def OnDraw(self):
        '''Drawcall, clear the stage, prepare a new frame and
        eventually swap buffers
        '''

        # Clear color and depth buffers.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # Activate the compiled shader program for use
        glUseProgram(self.sh_program)

        # Activate the vertex array buffer for the objects to draw
        self.triangle.arm_for_drawing()
        self.triangle.draw()

        # Swap the currently shown frame with the prepared new frame
        self.SwapBuffers()

        # Approximate how long the frame took
        self.calc_frametime()

    def _create_assets(self) -> None:
        """
            Create all of the assets needed for drawing.
        """
        # A triangle object (vertices and colours)
        self.triangle = Triangle()

        # Shader program
        vert_filepath = "shaders/vertex.glsl"
        frag_filepath = "shaders/fragment.glsl"
        self.sh_program = create_shader_program(vert_filepath, frag_filepath)

    def calc_frametime(self) -> None:
        """
            Calculate the frametime and framerate,
            and update the textbox.
        """
        current_time = time.time_ns()
        frametime = (current_time - self.last_time) / 1000000
        if frametime > 1000:
            frametime = 10
        framerate = int(1000 / frametime)
        self.last_time = current_time
        self.fps_status.SetLabel(f"Frametime: {frametime:.3f} ms, FPS: {framerate}")

    def destroy(self) -> None:
        '''Clean up before closing the window'''
        if self.triangle:
            self.triangle.destroy()
        if self.sh_program:
            glDeleteProgram(self.sh_program)


class OpenGLDemoWindow(wx.Frame):
    '''Creates the basic window with UI elements that hosts the glcanvas'''
    def __init__(self):
        super().__init__(parent=None,
        				  title='OpenGL 01: Triangle',
        				  size = (480, 480))

        topsizer = wx.BoxSizer(wx.VERTICAL)
        footer_sizer = wx.BoxSizer(wx.HORIZONTAL)

        fps_status = wx.StaticText(self, -1, "Frametime will be shown here.",
                                   style = wx.ST_ELLIPSIZE_END)
        footer_sizer.Add(fps_status, 1, wx.ALL, 12)
        footer_sizer.AddStretchSpacer(1)

        self.canvas = Canvas(self, fps_status)
        topsizer.Add(self.canvas, 1, wx.EXPAND)
        topsizer.Add(footer_sizer, 0, wx.EXPAND)

        close_button = wx.Button(self, wx.ID_CLOSE)
        footer_sizer.Add(close_button, 0, wx.ALL, 12)
        close_button.Bind(wx.EVT_BUTTON, self.on_close)

        self.SetSizer(topsizer)
        self.SetMinClientSize((312, 72))
        self.Show(True)

    def on_close(self, event):
        '''Clean up before closing the window'''
        self.canvas.destroy()
        self.Close()

if __name__ == '__main__':
    app = wx.App()
    frame = OpenGLDemoWindow()
    app.MainLoop()
