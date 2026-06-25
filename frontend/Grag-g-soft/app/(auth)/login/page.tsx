"use client"
import { Flex } from "antd"
import LoginForm from "../../features/auth/components/LoginForm"
export default function Login() {
    return (
        <Flex justify="center" align="center" className="bg-reg-500!">
            <LoginForm />
        </Flex>
    )
}