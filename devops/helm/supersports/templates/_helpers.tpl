{{- define "supersports.prefix" -}}
{{- .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}
{{- define "supersports.secret" -}}
{{- required "existingSecret must name an externally supplied Secret" .Values.existingSecret -}}
{{- end -}}
