# LocalStack Resource Provider Scaffolding v2
from __future__ import annotations

from pathlib import Path
from typing import Optional, TypedDict

import localstack.services.cloudformation.provider_utils as util
from localstack.services.cloudformation.resource_provider import (
    OperationStatus,
    ProgressEvent,
    Properties,
    ResourceProvider,
    ResourceRequest,
)


class EC2SecurityGroupProperties(TypedDict):
    GroupDescription: Optional[str]
    GroupId: Optional[str]
    GroupName: Optional[str]
    Id: Optional[str]
    SecurityGroupEgress: Optional[list[Egress]]
    SecurityGroupIngress: Optional[list[Ingress]]
    Tags: Optional[list[Tag]]
    VpcId: Optional[str]


class Ingress(TypedDict):
    IpProtocol: Optional[str]
    CidrIp: Optional[str]
    CidrIpv6: Optional[str]
    Description: Optional[str]
    FromPort: Optional[int]
    SourcePrefixListId: Optional[str]
    SourceSecurityGroupId: Optional[str]
    SourceSecurityGroupName: Optional[str]
    SourceSecurityGroupOwnerId: Optional[str]
    ToPort: Optional[int]


class Egress(TypedDict):
    IpProtocol: Optional[str]
    CidrIp: Optional[str]
    CidrIpv6: Optional[str]
    Description: Optional[str]
    DestinationPrefixListId: Optional[str]
    DestinationSecurityGroupId: Optional[str]
    FromPort: Optional[int]
    ToPort: Optional[int]


class Tag(TypedDict):
    Key: Optional[str]
    Value: Optional[str]


REPEATED_INVOCATION = "repeated_invocation"


def model_from_description(sg_description: dict) -> dict:
    model = {
        "Id": sg_description.get("GroupId"),
        "GroupId": sg_description.get("GroupId"),
        "GroupName": sg_description.get("GroupName"),
        "GroupDescription": sg_description.get("Description"),
        "SecurityGroupEgress": [],
        "SecurityGroupIngress": [],
        "Tags": sg_description.get("Tags", []),
    }

    for i, egress in enumerate(sg_description.get("IpPermissionsEgress", [])):
        for ip_range in egress.get("IpRanges", []):
            model["SecurityGroupEgress"].append(
                {
                    "CidrIp": ip_range.get("CidrIp"),
                    "FromPort": egress.get("FromPort", -1),
                    "IpProtocol": egress.get("IpProtocol", "-1"),
                    "ToPort": egress.get("ToPort", -1),
                }
            )

    for i, ingress in enumerate(sg_description.get("IpPermissions", [])):
        for ip_range in ingress.get("IpRanges", []):
            model["SecurityGroupIngress"].append(
                {
                    "CidrIp": ip_range.get("CidrIp"),
                    "FromPort": ingress.get("FromPort", -1),
                    "IpProtocol": ingress.get("IpProtocol", "-1"),
                    "ToPort": ingress.get("ToPort", -1),
                }
            )

    model["VpcId"] = sg_description.get("VpcId")
    return model


class EC2SecurityGroupProvider(ResourceProvider[EC2SecurityGroupProperties]):
    TYPE = "AWS::EC2::SecurityGroup"  # Autogenerated. Don't change
    SCHEMA = util.get_schema_path(Path(__file__))  # Autogenerated. Don't change

    def create(
        self,
        request: ResourceRequest[EC2SecurityGroupProperties],
    ) -> ProgressEvent[EC2SecurityGroupProperties]:
        """
        Create a new resource.

        Primary identifier fields:
          - /properties/Id

        Required properties:
          - GroupDescription

        Create-only properties:
          - /properties/GroupDescription
          - /properties/GroupName
          - /properties/VpcId

        Read-only properties:
          - /properties/Id
          - /properties/GroupId



        """
        model = request.desired_state
        ec2 = request.aws_client_factory.ec2

        params = {}

        if not model.get("GroupName"):
            params["GroupName"] = util.generate_default_name(
                request.stack_name, request.logical_resource_id
            )
        else:
            params["GroupName"] = model["GroupName"]

        if vpc_id := model.get("VpcId"):
            params["VpcId"] = vpc_id

        params["Description"] = model.get("GroupDescription", "")

        tags = [
            {"Key": "aws:cloudformation:logical-id", "Value": request.logical_resource_id},
            {"Key": "aws:cloudformation:stack-id", "Value": request.stack_id},
            {"Key": "aws:cloudformation:stack-name", "Value": request.stack_name},
        ]

        if model_tags := model.get("Tags"):
            tags += model_tags

        params["TagSpecifications"] = [{"ResourceType": "security-group", "Tags": tags}]

        response = ec2.create_security_group(**params)
        model["GroupId"] = response["GroupId"]

        # When you pass the logical ID of this resource to the intrinsic Ref function,
        # Ref returns the ID of the security group if you specified the VpcId property.
        # Otherwise, it returns the name of the security group.
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-securitygroup.html#aws-resource-ec2-securitygroup-return-values-ref
        if "VpcId" in model:
            model["Id"] = response["GroupId"]
        else:
            model["Id"] = params["GroupName"]

        return ProgressEvent(
            status=OperationStatus.SUCCESS,
            resource_model=model,
            custom_context=request.custom_context,
        )

    def read(
        self,
        request: ResourceRequest[EC2SecurityGroupProperties],
    ) -> ProgressEvent[EC2SecurityGroupProperties]:
        """
        Fetch resource information
        """

        model = request.desired_state

        security_group = request.aws_client_factory.ec2.describe_security_groups(
            GroupIds=[model["Id"]]
        )["SecurityGroups"][0]

        return ProgressEvent(
            status=OperationStatus.SUCCESS,
            resource_model=model_from_description(security_group),
        )

    def list(self, request: ResourceRequest[Properties]) -> ProgressEvent[Properties]:
        security_groups = request.aws_client_factory.ec2.describe_security_groups()[
            "SecurityGroups"
        ]

        return ProgressEvent(
            status=OperationStatus.SUCCESS,
            resource_models=[{"Id": description["GroupId"]} for description in security_groups],
        )

    def delete(
        self,
        request: ResourceRequest[EC2SecurityGroupProperties],
    ) -> ProgressEvent[EC2SecurityGroupProperties]:
        """
        Delete a resource


        """
        model = request.desired_state
        ec2 = request.aws_client_factory.ec2

        ec2.delete_security_group(GroupId=model["GroupId"])
        return ProgressEvent(
            status=OperationStatus.SUCCESS,
            resource_model=model,
            custom_context=request.custom_context,
        )

    def update(
        self,
        request: ResourceRequest[EC2SecurityGroupProperties],
    ) -> ProgressEvent[EC2SecurityGroupProperties]:
        """
        Update a resource


        """
        raise NotImplementedError
