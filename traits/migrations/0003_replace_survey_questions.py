from django.db import migrations


def replace_survey(apps, schema_editor):
    from traits.survey_definition import build_schema

    Survey = apps.get_model('traits', 'Survey')
    survey = Survey.objects.order_by('pk').first()
    if survey is None:
        Survey.objects.create(title='지원자 성향검사', schema=build_schema())
    else:
        survey.title = '지원자 성향검사'
        survey.schema = build_schema()
        survey.save(update_fields=['title', 'schema'])


class Migration(migrations.Migration):
    dependencies = [('traits', '0002_surveyresponse_candidate')]
    operations = [migrations.RunPython(replace_survey, migrations.RunPython.noop)]
