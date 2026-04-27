"use client";

import { useRouter } from "next/navigation";
import { Button, Typography } from "antd";
import {
  UserOutlined,
  MailOutlined,
  LockOutlined,
} from "@ant-design/icons";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { registerSchema, RegisterSchema } from "../validation/register.schema";
import { useRegister } from "../hooks/useRegister";
import { routes } from "../../../services/routes";
import styles from "../style/RegisterForm.module.css";
import FormField from "../../../components/ui/FormField";

const { Title, Text } = Typography;

export default function RegisterForm() {
  const router = useRouter();
  const { register, error, isSubmitting } = useRegister();

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterSchema>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      password: "",
      confirm_password: "",
    },
  });

  const onSubmit = (values: RegisterSchema) => register(values);

  return (
    <form className={styles.formWrapper} onSubmit={handleSubmit(onSubmit)}>
      <div className={styles.container}>
        
        {/* Title */}
        <div className={styles.titleWrapper}>
          <Title level={3} className={styles.title}>
            Register
          </Title>
        </div>

        {/* Server error */}
        {error && (
          <div className={styles.serverError}>
            <Text>{error}</Text>
          </div>
        )}

        {/* Name row */}
        <div className={styles.row}>
          <div className={styles.col}>
            <FormField
              name="first_name"
              control={control}
              label="First Name"
              error={errors.first_name?.message}
              prefix={<UserOutlined />}
            />
          </div>

          <div className={styles.col}>
            <FormField
              name="last_name"
              control={control}
              label="Last Name"
              error={errors.last_name?.message}
              prefix={<UserOutlined />}
            />
          </div>
        </div>

        {/* Email */}
        <FormField
          name="email"
          control={control}
          label="Email"
          error={errors.email?.message}
          prefix={<MailOutlined />}
        />

        {/* Password */}
        <FormField
          name="password"
          control={control}
          label="Password"
          error={errors.password?.message}
          prefix={<LockOutlined />}
          isPassword
        />

        {/* Confirm Password */}
        <FormField
          name="confirm_password"
          control={control}
          label="Confirm Password"
          error={errors.confirm_password?.message}
          prefix={<LockOutlined />}
          isPassword
        />

        {/* Submit */}
        <Button
          htmlType="submit"
          loading={isSubmitting}
          block
          className={styles.button}
        >
          {isSubmitting ? "Creating account…" : "Register"}
        </Button>

        {/* Footer */}
        <Text className={styles.footer}>
          Already have an account?{" "}
          <span
            onClick={() => router.push(routes.login)}
            className={styles.link}
          >
            Sign In
          </span>
        </Text>
      </div>
    </form>
  );
}