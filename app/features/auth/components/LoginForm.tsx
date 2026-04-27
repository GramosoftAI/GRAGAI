"use client";

import { useRouter } from "next/navigation";
import { Input, Button, Typography, Flex } from "antd";
import {
  UserOutlined,
  LockOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
} from "@ant-design/icons";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";
import { loginSchema, LoginSchema } from "../validation/login.schema";
import { useLogin } from "../hooks/useLogin";
import { routes } from "../../../services/routes";
import styles from "../style/LoginForm.module.css";

const { Title, Text } = Typography;

export default function LoginForm() {
  const router = useRouter();
  const { login, error, isSubmitting } = useLogin();

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginSchema>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = (values: LoginSchema) => login(values);

  return (
    <Flex className={styles.body}>
        <form className={styles.formWrapper} onSubmit={handleSubmit(onSubmit)}>
      <div className={styles.container}>
        
        {/* Title */}
        <div className={styles.titleWrapper}>
          <Title level={3} className={styles.title}>
            Login
          </Title>
        </div>

        {/* Server Error */}
        {error && (
          <div className={styles.errorBox}>
            <Text className={styles.errorTextServer}>{error}</Text>
          </div>
        )}

        {/* Email */}
        <div>
          <Text className={styles.label}>
            Email <span className={styles.required}>*</span>
          </Text>

          <Controller
            name="email"
            control={control}
            render={({ field }) => (
              <>
                <Input
                  {...field}
                  type="email"
                  autoComplete="username"
                  prefix={<UserOutlined style={{ color: "#4ade80" }} />}
                  variant="borderless"
                  className={styles.input}
                />
                {errors.email && (
                  <Text className={styles.errorText}>
                    {errors.email.message}
                  </Text>
                )}
              </>
            )}
          />
        </div>

        {/* Password */}
        <div>
          <Text className={styles.label}>
            Password <span className={styles.required}>*</span>
          </Text>

          <Controller
            name="password"
            control={control}
            render={({ field }) => (
              <>
                <Input.Password
                  {...field}
                  autoComplete="current-password"
                  prefix={<LockOutlined style={{ color: "#4ade80" }} />}
                  iconRender={(visible) =>
                    visible ? (
                      <EyeOutlined style={{ color: "#4ade80" }} />
                    ) : (
                      <EyeInvisibleOutlined style={{ color: "#4ade80" }} />
                    )
                  }
                  variant="borderless"
                  className={styles.input}
                />
                {errors.password && (
                  <Text className={styles.errorText}>
                    {errors.password.message}
                  </Text>
                )}
              </>
            )}
          />
        </div>

        {/* Submit */}
        <Button
          htmlType="submit"
          loading={isSubmitting}
          disabled={isSubmitting}
          block
          className={`${styles.button} ${
            isSubmitting ? styles.buttonDisabled : ""
          }`}
        >
          {isSubmitting ? "Signing in…" : "Login"}
        </Button>

        {/* Footer */}
        <Text className={styles.footerText}>
          Don&apos;t have an account?{" "}
          <span
            onClick={() => router.push(routes.register)}
            className={styles.link}
          >
            Sign Up
          </span>
        </Text>
      </div>
    </form>
          <Text style={{color:"#ffff"}}>
              hiii welcome
          </Text>
    </Flex>
  );
}