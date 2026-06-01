{{/*
Expand the name of the chart.
*/}}
{{- define "devops-copilot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "devops-copilot.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart name and version label value.
*/}}
{{- define "devops-copilot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "devops-copilot.labels" -}}
helm.sh/chart: {{ include "devops-copilot.chart" . }}
{{ include "devops-copilot.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: devops-copilot
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "devops-copilot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "devops-copilot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend selector labels.
*/}}
{{- define "devops-copilot.backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "devops-copilot.name" . }}-backend
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Frontend selector labels.
*/}}
{{- define "devops-copilot.frontend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "devops-copilot.name" . }}-frontend
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Postgres selector labels.
*/}}
{{- define "devops-copilot.postgres.selectorLabels" -}}
app.kubernetes.io/name: {{ include "devops-copilot.name" . }}-postgres
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend service account name.
*/}}
{{- define "devops-copilot.backend.serviceAccountName" -}}
{{- if .Values.backend.serviceAccount.create }}
{{- default (printf "%s-backend" (include "devops-copilot.fullname" .)) .Values.backend.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.backend.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
OpenRouter API key.
*/}}
{{- define "devops-copilot.openrouter.apiKey" -}}
{{- if .Values.openrouter.apiKeyExistingSecret }}
{{- printf "%s" .Values.openrouter.apiKeyExistingSecretKey }}
{{- else if .Values.openrouter.apiKey }}
{{- .Values.openrouter.apiKey | quote }}
{{- else }}
{{- fail "openrouter.apiKey is required (set openrouter.apiKey or openrouter.apiKeyExistingSecret)" }}
{{- end }}
{{- end }}
