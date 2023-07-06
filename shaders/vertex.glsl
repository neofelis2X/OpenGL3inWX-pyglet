#version 330 core

layout (location=0) in vec3 vertexPos;
layout (location=1) in vec3 vertexColor;

uniform float aspect;
float correctedY = vertexPos.y * aspect;

out vec3 fragmentColor;

void main()
{
    gl_Position = vec4(vertexPos.x, correctedY, vertexPos.z, 1.0);
    fragmentColor = vertexColor;
}