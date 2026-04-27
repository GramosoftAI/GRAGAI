"use client"
import { Button, Flex } from 'antd'
import React from 'react'
import { useRouter } from 'next/navigation'


export default function NavBar() {
  const router = useRouter();
  return (
    <div className='w-full h-[60px] bg-black p-3'>
      <Flex justify='space-between'>
        <div><span className='text-white'>G-</span><span className='text-green-300'>rag AI</span></div>
        <div className='flex gap-4'>
          <Button onClick={() => router.push("/login")} className='text-white bg-green-600! rounded p-2 text-white font-bold '>Login</Button>
          {/* <a href="/register" className='text-white bg-green-600! rounded p-2 text-white font-bold'>Register</a> */}
        </div>
      </Flex>
    </div>
  )
}
