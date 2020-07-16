# quickstart-lex-kendra
## COVID 19 Lex-Kendra Chatbot on AWS

This Quick Start deploys an Amazon Lex chatbot with Amazon Kendra search capabilities to answer user queries regarding the recent pandemic on the Amazon Web Services (AWS) Cloud in about 35 minutes.
This Quick Start is for users who want to build and test a proof of concept or to create a production-ready solution with a deployment of a Amazon Lex chatbot linked to a Kendra index, datasource and FAQs.

This integration of the COVID 19 Lex chatbot with Kendra is a multifunctional chatbot, that can answer user queries based on pre-configured intents as well as query an S3 data repository containing the latest research using Amazon Kendra search capabilities.

This Quick Start is available in all the supported regions like us-east-1 (N. Virginia), us-west-2 (Oregon) and eu-west-1 (Ireland).

You can use the AWS CloudFormation templates (templates/lex_bot_kendra_master.template) included with the Quick Start to deploy COVID 19 Lex-Kendra chatbot in your AWS account in about 35 minutes.

This Quick Start automates the following:

- Deploying the COVID 19 Amazon Lex chatbot and Kendra Index with COVID 19 data repository
- Deploying an Amazon Lex chatbot and Kendra Index with custom intents and data repository

![Process flow diagram](https://github.com/aws-quickstart/quickstart-quantiphi-lex-kendra-backend/raw/develop/Process%20Flow.jpg)

The Process Flow diagram is present above.

### Pre-requisites
Please make sure you have the following pre-requisites, before launching the CloudFormation templates to deploy the Quick Start.

1. An AWS Account.
2. An S3 bucket, which contains the documents related to COVID-19 that are used by Kendra to index and query. This S3 bucket is the document repository which will be used as a data source by Kendra.

### Deployment steps

1. Download [FAQ file](https://github.com/aws-quickstart/quickstart-quantiphi-lex-kendra-backend/blob/master/assets/FAQ-document/COVID_FAQ.csv) from the repository and upload it into the S3 bucket (mentioned in pre-requisites section above) which is used as document repository.
2. Click [Deploy](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/template?stackName=lex-kendra&templateURL=https://aws-quickstart.s3.amazonaws.com/quickstart-quantiphi-lex-kendra-backend/templates/lex_bot_kendra_master.template) to launch the CloudFormation template in your AWS Account. Click "Next".
3. Provide S3 bucket name (from the pre-requisite section above) for parameter 'S3 bucket with documents', and click Next.
4. On 'Configure stack options' screen, click Next.
5. Review the details, provide IAM_CAPABILITIES by clicking the check boxes under 'Capabilities' section, and click 'Create stack'. It will take approximately 25 minutes to create the stack.
5. Once the stack creation is complete, go to Amazon Lex console, find the bot named 'covid_nineteen_bot' and click 'Test Chatbot' to start the conversation.